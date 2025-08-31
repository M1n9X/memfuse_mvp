"""
Sessions API endpoints for MemFuse.
Handles session CRUD operations and user-agent relationships.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Path
import psycopg

from memfuse.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_db() -> Database:
    """Dependency injection placeholder - will be overridden by main app."""
    raise NotImplementedError("Database dependency not configured")


# Make get_db accessible for dependency override
router.get_db = get_db


@router.post("/", response_model=dict)
async def create_session(session_data: dict, db: Database = Depends(get_db)):
    """Create a new session."""
    try:
        user_id = session_data.get("user_id")
        agent_id = session_data.get("agent_id")
        
        if not user_id or not agent_id:
            raise HTTPException(status_code=400, detail="user_id and agent_id are required")
        
        name = session_data.get("name")
        metadata = session_data.get("metadata", {})
        
        session_id = str(uuid.uuid4())
        
        with db.connect() as conn, conn.cursor() as cur:
            # Verify user and agent exist
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")
                
            cur.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Create session
            cur.execute(
                """
                INSERT INTO sessions (id, user_id, agent_id, name, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING id, user_id, agent_id, name, metadata, created_at, updated_at
                """,
                (session_id, user_id, agent_id, name, psycopg.types.json.Json(metadata))
            )
            row = cur.fetchone()
            
        return {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "agent_id": str(row[2]),
            "name": row[3],
            "metadata": row[4] or {},
            "created_at": row[5].isoformat(),
            "updated_at": row[6].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[dict])
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(50, le=1000, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    db: Database = Depends(get_db)
):
    """List sessions with optional filtering."""
    try:
        conditions = []
        params = []
        
        if user_id:
            conditions.append("s.user_id = %s")
            params.append(user_id)
            
        if agent_id:
            conditions.append("s.agent_id = %s")
            params.append(agent_id)
            
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
            
        params.extend([limit, offset])
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT s.id, s.user_id, s.agent_id, s.name, s.metadata, s.created_at, s.updated_at,
                       u.name as user_name, a.name as agent_name
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                JOIN agents a ON s.agent_id = a.id
                {where_clause}
                ORDER BY s.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params
            )
            rows = cur.fetchall()
            
        return [
            {
                "id": str(row[0]),
                "user_id": str(row[1]),
                "agent_id": str(row[2]),
                "name": row[3],
                "metadata": row[4] or {},
                "created_at": row[5].isoformat(),
                "updated_at": row[6].isoformat(),
                "user_name": row[7],
                "agent_name": row[8]
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=dict)
async def get_session(session_id: str = Path(..., description="Session ID"), db: Database = Depends(get_db)):
    """Get a specific session by ID."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.user_id, s.agent_id, s.name, s.metadata, s.created_at, s.updated_at,
                       u.name as user_name, a.name as agent_name
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                JOIN agents a ON s.agent_id = a.id
                WHERE s.id = %s
                """,
                (session_id,)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "agent_id": str(row[2]),
            "name": row[3],
            "metadata": row[4] or {},
            "created_at": row[5].isoformat(),
            "updated_at": row[6].isoformat(),
            "user_name": row[7],
            "agent_name": row[8]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{session_id}", response_model=dict)
async def update_session(
    session_id: str = Path(..., description="Session ID"),
    session_data: dict = None,
    db: Database = Depends(get_db)
):
    """Update a session."""
    try:
        if not session_data:
            raise HTTPException(status_code=400, detail="Update data is required")
            
        # Build dynamic update query
        update_fields = []
        params = []
        
        if "name" in session_data:
            update_fields.append("name = %s")
            params.append(session_data["name"])
            
        if "metadata" in session_data:
            update_fields.append("metadata = %s::jsonb")
            params.append(psycopg.types.json.Json(session_data["metadata"]))
            
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        params.append(session_id)
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE sessions 
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, user_id, agent_id, name, metadata, created_at, updated_at
                """,
                params
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "agent_id": str(row[2]),
            "name": row[3],
            "metadata": row[4] or {},
            "created_at": row[5].isoformat(),
            "updated_at": row[6].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{session_id}")
async def delete_session(session_id: str = Path(..., description="Session ID"), db: Database = Depends(get_db)):
    """Delete a session and all associated messages."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}/stats", response_model=dict)
async def get_session_stats(session_id: str = Path(..., description="Session ID"), db: Database = Depends(get_db)):
    """Get session statistics including message count and memory usage."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            # Check if session exists
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Get message count
            cur.execute("SELECT COUNT(*) FROM messages WHERE session_id = %s", (session_id,))
            message_count = cur.fetchone()[0]
            
            # Get structured memory count (using session mapping)
            cur.execute(
                """
                SELECT COUNT(*) FROM structured_memory sm
                JOIN session_mappings map ON sm.session_id = map.old_session_id
                WHERE map.new_session_id = %s
                """,
                (session_id,)
            )
            structured_count = cur.fetchone()[0] or 0
            
        return {
            "session_id": session_id,
            "message_count": message_count,
            "structured_memory_count": structured_count,
            "last_activity": datetime.now().isoformat()  # TODO: Get actual last message time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session stats {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
