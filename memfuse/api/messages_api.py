"""
Messages API endpoints for MemFuse.
Handles message CRUD operations, chat functionality, and M3 workflow logging.
"""

import logging
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
import psycopg

from memfuse.db import Database
from memfuse.rag import RAGService
from memfuse.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["messages"])


def get_db() -> Database:
    """Dependency injection placeholder - will be overridden by main app."""
    raise NotImplementedError("Database dependency not configured")


def get_rag() -> RAGService:
    """Dependency injection placeholder - will be overridden by main app."""
    raise NotImplementedError("RAG pipeline dependency not configured")


def get_orchestrator() -> Orchestrator:
    """Dependency injection placeholder - will be overridden by main app."""
    raise NotImplementedError("Orchestrator dependency not configured")


# Make dependencies accessible for dependency override
router.get_db = get_db
router.get_rag = get_rag
router.get_orchestrator = get_orchestrator


@router.post("/sessions/{session_id}/messages", response_model=dict)
async def create_message(
    session_id: str = Path(..., description="Session ID"),
    message_data: dict = Body(...),
    tag: Optional[str] = Query(None, description="Use 'm3' for M3 workflow"),
    db: Database = Depends(get_db),
    rag: RAGService = Depends(get_rag),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    统一的消息创建接口，支持长上下文和M3工作流。

    - 默认模式: 创建消息，如果是用户消息则触发RAG回复
    - tag=m3: 创建消息并启用M3工作流处理复杂任务
    """
    try:
        # Verify session exists
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Session not found")

        # 支持两种输入格式
        if "messages" in message_data:
            # 批量消息格式（兼容原有add_messages）
            messages_list = message_data["messages"]
            if not messages_list:
                raise HTTPException(status_code=400, detail="messages list cannot be empty")

            # 处理批量消息
            message_ids = []
            for msg in messages_list:
                msg_id = await _create_single_message(db, session_id, msg)
                message_ids.append(msg_id)

            return {"message_ids": message_ids}
        else:
            # 单条消息格式
            role = message_data.get("role")
            content = message_data.get("content")

            if not content:
                raise HTTPException(status_code=400, detail="content is required")

            # 如果没有指定role且有content，默认为user消息并触发AI回复
            if not role:
                role = "user"

            if role not in ["user", "assistant", "system"]:
                raise HTTPException(status_code=400, detail="role must be one of: user, assistant, system")

            # 创建用户消息
            user_message_id = await _create_single_message(db, session_id, message_data)

            # 如果是用户消息，触发AI回复
            if role == "user":
                ai_response = await _generate_ai_response(
                    session_id, content, tag, db, rag, orchestrator
                )

                # 创建AI回复消息
                ai_message_data = {
                    "role": "assistant",
                    "content": ai_response["content"],
                    "metadata": ai_response.get("metadata", {}),
                    "tags": ai_response.get("tags", []),
                    "workflow_id": ai_response.get("workflow_id"),
                    "step_index": ai_response.get("step_index")
                }

                ai_message_id = await _create_single_message(db, session_id, ai_message_data)

                return {
                    "user_message_id": user_message_id,
                    "ai_message_id": ai_message_id,
                    "content": ai_response["content"],
                    "workflow_used": ai_response.get("workflow_id")
                }
            else:
                # 非用户消息，直接返回
                return {"message_id": user_message_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/messages", response_model=List[dict])
async def list_messages(
    session_id: str = Path(..., description="Session ID"),
    role: Optional[str] = Query(None, description="Filter by message role"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (any match)"),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    content_search: Optional[str] = Query(None, description="Search in message content"),
    limit: int = Query(50, le=1000, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    db: Database = Depends(get_db)
):
    """List messages in a session with optional filtering."""
    try:
        # Verify session exists
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Session not found")
        
        conditions = ["session_id = %s"]
        params = [session_id]
        
        if role:
            conditions.append("role = %s")
            params.append(role)
            
        if workflow_id:
            conditions.append("workflow_id = %s")
            params.append(workflow_id)
            
        if content_search:
            conditions.append("content ILIKE %s")
            params.append(f"%{content_search}%")
            
        if tags:
            # Check if any of the provided tags match
            conditions.append("tags && %s")
            params.append(tags)
            
        where_clause = "WHERE " + " AND ".join(conditions)
        params.extend([limit, offset])
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, session_id, role, content, metadata, tags, workflow_id, step_index, created_at
                FROM messages 
                {where_clause}
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                params
            )
            rows = cur.fetchall()
            
        return [
            {
                "id": str(row[0]),
                "session_id": str(row[1]),
                "role": row[2],
                "content": row[3],
                "metadata": row[4] or {},
                "tags": row[5] or [],
                "workflow_id": str(row[6]) if row[6] else None,
                "step_index": row[7],
                "created_at": row[8].isoformat()
            }
            for row in rows
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/messages/{message_id}", response_model=dict)
async def get_message(
    session_id: str = Path(..., description="Session ID"),
    message_id: str = Path(..., description="Message ID"),
    db: Database = Depends(get_db)
):
    """Get a specific message by ID."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, role, content, metadata, tags, workflow_id, step_index, created_at
                FROM messages 
                WHERE id = %s AND session_id = %s
                """,
                (message_id, session_id)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")
            
        return {
            "id": str(row[0]),
            "session_id": str(row[1]),
            "role": row[2],
            "content": row[3],
            "metadata": row[4] or {},
            "tags": row[5] or [],
            "workflow_id": str(row[6]) if row[6] else None,
            "step_index": row[7],
            "created_at": row[8].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message {message_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_message(
    session_id: str = Path(..., description="Session ID"),
    message_id: str = Path(..., description="Message ID"),
    db: Database = Depends(get_db)
):
    """Delete a message."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM messages WHERE id = %s AND session_id = %s",
                (message_id, session_id)
            )

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Message not found")

        return {"message": "Message deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions/{session_id}/chat", response_model=dict)
async def chat(
    session_id: str = Path(..., description="Session ID"),
    chat_request: dict = Body(...),
    tag: Optional[str] = Query(None, description="Use 'm3' to enable M3 workflow"),
    db: Database = Depends(get_db),
    rag: RAGService = Depends(get_rag),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Send a message and get AI response.

    - Default: Uses RAG for simple Q&A
    - tag=m3: Enables M3 workflow for complex tasks
    """
    try:
        # Verify session exists
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404, detail="Session not found"
                )

        content = chat_request.get("content")
        if not content:
            raise HTTPException(status_code=400, detail="content is required")

        metadata = chat_request.get("metadata", {})
        # 统一使用tag参数控制M3工作流
        enable_m3 = (tag == "m3") or chat_request.get("enable_m3", False)

        # Create user message
        user_message_id = str(uuid.uuid4())
        tags = ["m3"] if enable_m3 else []

        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (id, session_id, role, content, metadata, tags)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                """,
                (user_message_id, session_id, "user", content,
                 psycopg.types.json.Json(metadata), tags)
            )

        # Get session mapping for backward compatibility with existing RAG system
        old_session_id = None
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """SELECT old_session_id FROM session_mappings
                   WHERE new_session_id = %s""",
                (session_id,)
            )
            row = cur.fetchone()
            if row:
                old_session_id = row[0]
            else:
                # Create a mapping for this session
                old_session_id = f"api_session_{session_id}"
                cur.execute(
                    """INSERT INTO session_mappings
                       (old_session_id, new_session_id) VALUES (%s, %s)""",
                    (old_session_id, session_id)
                )

        # Determine if this is a complex task requiring M3/orchestrator
        workflow_used = None
        ai_response = None

        if enable_m3:
            # Use orchestrator for complex tasks with M3 support
            try:
                ai_response = orchestrator.handle_request(old_session_id, content)
                workflow_used = str(uuid.uuid4())  # 使用UUID格式

                # Log M3 workflow usage
                if workflow_used:
                    step_message_id = str(uuid.uuid4())
                    with db.connect() as conn, conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO messages
                            (id, session_id, role, content, metadata,
                             tags, workflow_id, step_index)
                            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                            """,
                            (step_message_id, session_id, "system",
                             "M3 workflow executed for complex task",
                             psycopg.types.json.Json({"m3_enabled": True}),
                             ["m3", "workflow"], workflow_used, 0)
                        )

            except Exception as e:
                logger.warning(f"Orchestrator failed, falling back to RAG: {e}")
                ai_response = rag.chat(old_session_id, content)
        else:
            # Use simple RAG for basic queries
            ai_response = rag.chat(old_session_id, content)

        if not ai_response:
            raise HTTPException(
                status_code=500, detail="Failed to generate response"
            )

        # Create AI response message
        ai_message_id = str(uuid.uuid4())
        ai_metadata = {"user_message_id": user_message_id}
        if workflow_used:
            ai_metadata["workflow_id"] = workflow_used

        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages
                (id, session_id, role, content, metadata, tags, workflow_id)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id, session_id, role, content, metadata,
                          tags, workflow_id, created_at
                """,
                (ai_message_id, session_id, "assistant", ai_response,
                 psycopg.types.json.Json(ai_metadata), tags, workflow_used)
            )
            row = cur.fetchone()

        return {
            "message_id": str(row[0]),
            "content": row[3],
            "metadata": row[4] or {},
            "workflow_used": workflow_used,
            "created_at": row[7].isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions/{session_id}/messages/batch", response_model=dict)
async def create_messages_batch(
    session_id: str = Path(..., description="Session ID"),
    messages_data: dict = Body(...),
    db: Database = Depends(get_db)
):
    """Create multiple messages in batch (useful for workflow logging)."""
    try:
        # Verify session exists
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404, detail="Session not found"
                )

        messages = messages_data.get("messages", [])
        if not messages:
            raise HTTPException(
                status_code=400, detail="messages array is required"
            )

        created_messages = []

        with db.connect() as conn, conn.cursor() as cur:
            for msg_data in messages:
                role = msg_data.get("role")
                content = msg_data.get("content")

                if not role or not content:
                    continue  # Skip invalid messages

                if role not in ["user", "assistant", "system"]:
                    continue  # Skip invalid roles

                metadata = msg_data.get("metadata", {})
                tags = msg_data.get("tags", [])
                workflow_id = msg_data.get("workflow_id")
                step_index = msg_data.get("step_index")

                message_id = str(uuid.uuid4())

                cur.execute(
                    """
                    INSERT INTO messages
                    (id, session_id, role, content, metadata,
                     tags, workflow_id, step_index)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (message_id, session_id, role, content,
                     psycopg.types.json.Json(metadata),
                     tags, workflow_id, step_index)
                )
                row = cur.fetchone()
                created_messages.append({
                    "id": str(row[0]),
                    "created_at": row[1].isoformat()
                })

        return {
            "created_count": len(created_messages),
            "messages": created_messages
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 辅助函数

async def _create_single_message(db: Database, session_id: str, message_data: dict) -> str:
    """创建单条消息的辅助函数。"""
    role = message_data.get("role", "user")
    content = message_data.get("content", "")
    metadata = message_data.get("metadata", {})
    tags = message_data.get("tags", [])
    workflow_id = message_data.get("workflow_id")
    step_index = message_data.get("step_index")

    message_id = str(uuid.uuid4())

    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (id, session_id, role, content, metadata, tags, workflow_id, step_index)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            """,
            (message_id, session_id, role, content,
             psycopg.types.json.Json(metadata), tags, workflow_id, step_index)
        )

    return message_id


async def _generate_ai_response(
    session_id: str, content: str, tag: Optional[str],
    db: Database, rag: RAGService, orchestrator: Orchestrator
) -> dict:
    """生成AI回复的辅助函数。"""
    # 获取session mapping用于RAG兼容性
    old_session_id = None
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT old_session_id FROM session_mappings WHERE new_session_id = %s",
            (session_id,)
        )
        row = cur.fetchone()
        if row:
            old_session_id = row[0]
        else:
            # 创建新的mapping
            old_session_id = f"api_session_{int(time.time())}"
            cur.execute(
                "INSERT INTO session_mappings (old_session_id, new_session_id) VALUES (%s, %s)",
                (old_session_id, session_id)
            )

    # 根据tag决定处理方式
    if tag == "m3":
        # 使用M3工作流
        try:
            ai_response = orchestrator.handle_request(old_session_id, content)
            workflow_used = str(uuid.uuid4())  # 使用UUID格式

            return {
                "content": ai_response,
                "metadata": {"m3_enabled": True, "workflow_name": f"m3_workflow_{int(time.time())}"},
                "tags": ["m3", "workflow"],
                "workflow_id": workflow_used,
                "step_index": 0
            }
        except Exception as e:
            logger.warning(f"M3 workflow failed, falling back to RAG: {e}")
            # 降级到RAG
            ai_response = rag.chat(old_session_id, content)
            return {
                "content": ai_response,
                "metadata": {"m3_fallback": True},
                "tags": ["rag_fallback"]
            }
    else:
        # 使用普通RAG
        ai_response = rag.chat(old_session_id, content)
        return {
            "content": ai_response,
            "metadata": {"processing_type": "rag"},
            "tags": ["rag"]
        }
