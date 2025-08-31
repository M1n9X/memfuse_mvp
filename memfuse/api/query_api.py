"""
Query API for MemFuse - 实现记忆检索和查询功能
"""

import logging
import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
import psycopg

from ..db import Database
from ..rag import RAGService
from ..retrieval import BasicRetrievalStrategy
from ..embeddings import JinaEmbeddingClient
from ..config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["query"])

# Dependency injection placeholders
def get_db() -> Database:
    """Database dependency - will be overridden by main app."""
    raise NotImplementedError("Database dependency not configured")

def get_rag() -> RAGService:
    """RAG service dependency - will be overridden by main app."""
    raise NotImplementedError("RAG service dependency not configured")

# Make dependencies accessible for override
router.get_db = get_db
router.get_rag = get_rag


@router.post("/users/{user_id}/query")
async def query_user_memories(
    user_id: str = Path(..., description="User ID"),
    query_data: Dict[str, Any] = Body(...),
    tag: Optional[str] = Query(None, description="Use 'm3' to focus on workflow memories"),
    db: Database = Depends(get_db),
    rag: RAGService = Depends(get_rag)
):
    """
    统一的用户记忆查询接口。

    支持两种模式：
    - 默认模式: 查询所有类型的记忆（消息、知识库等）
    - tag=m3: 重点查询M3工作流相关的记忆和经验

    这个接口统一了长上下文和Workflow的检索操作。
    """
    try:
        # 验证用户存在
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")
        
        # 提取查询参数
        query = query_data.get("query", "")
        session_id = query_data.get("session_id")
        agent_id = query_data.get("agent_id")
        top_k = min(query_data.get("top_k", 5), 50)  # 限制最大50个结果

        # 根据tag参数调整检索策略
        if tag == "m3":
            # M3模式：重点检索工作流相关记忆
            include_messages = query_data.get("include_messages", True)
            include_knowledge = query_data.get("include_knowledge", False)
            include_workflows = query_data.get("include_workflows", True)
        else:
            # 默认模式：检索所有类型记忆
            include_messages = query_data.get("include_messages", True)
            include_knowledge = query_data.get("include_knowledge", True)
            include_workflows = query_data.get("include_workflows", False)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        results = []
        
        # 1. 查询消息记忆 (如果启用)
        if include_messages:
            message_results = await _query_message_memories(
                db, user_id, query, session_id, agent_id, top_k
            )
            results.extend(message_results)
        
        # 2. 查询知识库 (如果启用)
        if include_knowledge:
            knowledge_results = await _query_knowledge_base(
                rag, query, session_id, top_k
            )
            results.extend(knowledge_results)
        
        # 3. 查询工作流经验 (如果启用)
        if include_workflows:
            workflow_results = await _query_workflow_memories(
                db, user_id, query, session_id, top_k
            )
            results.extend(workflow_results)
        
        # 4. 去重和排序
        unique_results = _deduplicate_and_rank(results, top_k)
        
        return {
            "data": {
                "results": unique_results,
                "query": query,
                "total_found": len(unique_results),
                "search_scope": {
                    "messages": include_messages,
                    "knowledge": include_knowledge,
                    "workflows": include_workflows
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/sessions/{session_id}/query")
async def query_session_memories(
    session_id: str = Path(..., description="Session ID"),
    query_data: Dict[str, Any] = Body(...),
    db: Database = Depends(get_db),
    rag: RAGService = Depends(get_rag)
):
    """
    Query memories within a specific session.
    
    Focused on session-specific content:
    - Session messages and conversations
    - Session-specific knowledge chunks
    - Session workflow history
    """
    try:
        # 验证会话存在
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, user_id FROM sessions WHERE id = %s", (session_id,))
            session_row = cur.fetchone()
            if not session_row:
                raise HTTPException(status_code=404, detail="Session not found")
        
        user_id = session_row[1]
        query = query_data.get("query", "")
        top_k = min(query_data.get("top_k", 10), 50)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        results = []
        
        # 1. 查询会话消息
        session_messages = await _query_session_messages(db, session_id, query, top_k)
        results.extend(session_messages)
        
        # 2. 查询会话相关知识块
        session_chunks = await _query_session_chunks(rag, session_id, query, top_k)
        results.extend(session_chunks)
        
        # 3. 查询会话工作流
        session_workflows = await _query_session_workflows(db, session_id, query, top_k)
        results.extend(session_workflows)
        
        # 去重和排序
        unique_results = _deduplicate_and_rank(results, top_k)
        
        return {
            "data": {
                "results": unique_results,
                "query": query,
                "session_id": session_id,
                "total_found": len(unique_results)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session query failed: {str(e)}")


@router.post("/workflows/{workflow_id}/query")
async def query_workflow_memories(
    workflow_id: str = Path(..., description="Workflow ID"),
    query_data: Dict[str, Any] = Body(...),
    db: Database = Depends(get_db)
):
    """
    Query memories related to a specific workflow.
    
    Retrieves:
    - Workflow execution steps
    - Related messages and context
    - Lessons learned from similar workflows
    """
    try:
        query = query_data.get("query", "")
        top_k = min(query_data.get("top_k", 10), 50)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # 查询工作流相关记忆
        workflow_results = await _query_specific_workflow(db, workflow_id, query, top_k)
        
        return {
            "data": {
                "results": workflow_results,
                "query": query,
                "workflow_id": workflow_id,
                "total_found": len(workflow_results)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow query failed: {str(e)}")


# 辅助函数

async def _query_message_memories(
    db: Database, user_id: str, query: str, session_id: Optional[str], 
    agent_id: Optional[str], top_k: int
) -> List[Dict[str, Any]]:
    """查询消息记忆。"""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            # 构建查询条件
            where_conditions = ["s.user_id = %s"]
            params = [user_id]
            
            if session_id:
                where_conditions.append("m.session_id = %s")
                params.append(session_id)
            
            if agent_id:
                where_conditions.append("s.agent_id = %s")
                params.append(agent_id)
            
            # 使用全文搜索查询消息
            where_conditions.append("m.content ILIKE %s")
            params.append(f"%{query}%")
            
            query_sql = f"""
                SELECT m.id, m.content, m.role, m.created_at, m.metadata,
                       s.name as session_name, m.session_id
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE {' AND '.join(where_conditions)}
                ORDER BY m.created_at DESC
                LIMIT %s
            """
            params.append(top_k)
            
            cur.execute(query_sql, params)
            rows = cur.fetchall()
            
            return [
                {
                    "type": "message",
                    "id": row[0],
                    "content": row[1],
                    "role": row[2],
                    "created_at": row[3].isoformat(),
                    "metadata": row[4] or {},
                    "session_name": row[5],
                    "session_id": row[6],
                    "relevance_score": 0.8  # 基于文本匹配的固定分数
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Message query failed: {e}")
        return []


async def _query_knowledge_base(
    rag: RAGService, query: str, session_id: Optional[str], top_k: int
) -> List[Dict[str, Any]]:
    """查询知识库。"""
    try:
        # 使用RAG的检索策略
        if rag.retrieval is None:
            rag.retrieval = BasicRetrievalStrategy(rag.db, rag.embedder, rag.settings)
        
        # 如果没有session_id，使用临时session
        search_session = session_id or "temp_query_session"
        
        retrieved_chunks = rag.retrieval.retrieve(search_session, query, [])
        
        return [
            {
                "type": "knowledge",
                "content": chunk.content,
                "source": chunk.source,
                "relevance_score": chunk.score,
                "metadata": {"chunk_type": "knowledge_base"}
            }
            for chunk in retrieved_chunks[:top_k]
        ]
    except Exception as e:
        logger.error(f"Knowledge query failed: {e}")
        return []


async def _query_workflow_memories(
    db: Database, user_id: str, query: str, session_id: Optional[str], top_k: int
) -> List[Dict[str, Any]]:
    """查询工作流记忆。"""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            # 查询工作流相关消息
            where_conditions = ["s.user_id = %s", "m.workflow_id IS NOT NULL"]
            params = [user_id]
            
            if session_id:
                where_conditions.append("m.session_id = %s")
                params.append(session_id)
            
            # 查询工作流内容
            where_conditions.append("m.content ILIKE %s")
            params.append(f"%{query}%")
            
            query_sql = f"""
                SELECT m.id, m.content, m.workflow_id, m.step_index, 
                       m.created_at, m.metadata, s.name as session_name
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE {' AND '.join(where_conditions)}
                ORDER BY m.created_at DESC
                LIMIT %s
            """
            params.append(top_k)
            
            cur.execute(query_sql, params)
            rows = cur.fetchall()
            
            return [
                {
                    "type": "workflow",
                    "id": row[0],
                    "content": row[1],
                    "workflow_id": row[2],
                    "step_index": row[3],
                    "created_at": row[4].isoformat(),
                    "metadata": row[5] or {},
                    "session_name": row[6],
                    "relevance_score": 0.9  # 工作流记忆通常更相关
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Workflow query failed: {e}")
        return []


async def _query_session_messages(
    db: Database, session_id: str, query: str, top_k: int
) -> List[Dict[str, Any]]:
    """查询会话内消息。"""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, content, role, created_at, metadata
                FROM messages
                WHERE session_id = %s AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (session_id, f"%{query}%", top_k))
            
            rows = cur.fetchall()
            
            return [
                {
                    "type": "session_message",
                    "id": row[0],
                    "content": row[1],
                    "role": row[2],
                    "created_at": row[3].isoformat(),
                    "metadata": row[4] or {},
                    "relevance_score": 0.85
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Session message query failed: {e}")
        return []


async def _query_session_chunks(
    rag: RAGService, session_id: str, query: str, top_k: int
) -> List[Dict[str, Any]]:
    """查询会话相关知识块。"""
    try:
        if rag.retrieval is None:
            rag.retrieval = BasicRetrievalStrategy(rag.db, rag.embedder, rag.settings)
        
        retrieved_chunks = rag.retrieval.retrieve(session_id, query, [])
        
        return [
            {
                "type": "session_chunk",
                "content": chunk.content,
                "source": chunk.source,
                "relevance_score": chunk.score,
                "metadata": {"session_specific": True}
            }
            for chunk in retrieved_chunks[:top_k]
        ]
    except Exception as e:
        logger.error(f"Session chunk query failed: {e}")
        return []


async def _query_session_workflows(
    db: Database, session_id: str, query: str, top_k: int
) -> List[Dict[str, Any]]:
    """查询会话工作流。"""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, content, workflow_id, step_index, created_at, metadata
                FROM messages
                WHERE session_id = %s AND workflow_id IS NOT NULL 
                AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (session_id, f"%{query}%", top_k))
            
            rows = cur.fetchall()
            
            return [
                {
                    "type": "session_workflow",
                    "id": row[0],
                    "content": row[1],
                    "workflow_id": row[2],
                    "step_index": row[3],
                    "created_at": row[4].isoformat(),
                    "metadata": row[5] or {},
                    "relevance_score": 0.9
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Session workflow query failed: {e}")
        return []


async def _query_specific_workflow(
    db: Database, workflow_id: str, query: str, top_k: int
) -> List[Dict[str, Any]]:
    """查询特定工作流的记忆。"""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT m.id, m.content, m.step_index, m.created_at, m.metadata,
                       s.name as session_name, s.id as session_id
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.workflow_id = %s AND m.content ILIKE %s
                ORDER BY m.step_index ASC, m.created_at ASC
                LIMIT %s
            """, (workflow_id, f"%{query}%", top_k))
            
            rows = cur.fetchall()
            
            return [
                {
                    "type": "workflow_step",
                    "id": row[0],
                    "content": row[1],
                    "step_index": row[2],
                    "created_at": row[3].isoformat(),
                    "metadata": row[4] or {},
                    "session_name": row[5],
                    "session_id": row[6],
                    "workflow_id": workflow_id,
                    "relevance_score": 0.95
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Specific workflow query failed: {e}")
        return []


def _deduplicate_and_rank(results: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """去重并按相关性排序结果。"""
    # 按内容去重
    seen_content = set()
    unique_results = []
    
    for result in results:
        content_key = result.get("content", "")[:100]  # 使用前100字符作为去重键
        if content_key not in seen_content:
            seen_content.add(content_key)
            unique_results.append(result)
    
    # 按相关性分数排序
    unique_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    return unique_results[:top_k]
