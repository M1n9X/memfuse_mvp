"""
Extended database operations for API endpoints.
Handles the new schema with users, agents, sessions, and messages.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

import psycopg
from memfuse.db import Database

logger = logging.getLogger(__name__)


class APIDatabase:
    """Extended database operations for API endpoints."""
    
    def __init__(self, db_manager: Database):
        self.db = db_manager
    
    # Users operations
    def create_user(self, name: str, email: Optional[str] = None, 
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, name, email, metadata)
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING id, name, email, metadata, created_at, updated_at
                """,
                (user_id, name, email, psycopg.types.json.Json(metadata))
            )
            row = cur.fetchone()
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "metadata": row[3] or {},
            "created_at": row[4],
            "updated_at": row[5]
        }
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, metadata, created_at, updated_at
                FROM users WHERE id = %s
                """,
                (user_id,)
            )
            row = cur.fetchone()
            
        if not row:
            return None
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "metadata": row[3] or {},
            "created_at": row[4],
            "updated_at": row[5]
        }
    
    def get_user_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get user by name."""
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, metadata, created_at, updated_at
                FROM users WHERE name = %s
                """,
                (name,)
            )
            row = cur.fetchone()
            
        if not row:
            return None
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "metadata": row[3] or {},
            "created_at": row[4],
            "updated_at": row[5]
        }
    
    # Agents operations
    def create_agent(self, name: str, agent_type: str = "assistant",
                    description: Optional[str] = None,
                    config: Optional[Dict[str, Any]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new agent."""
        agent_id = str(uuid.uuid4())
        config = config or {}
        metadata = metadata or {}
        
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agents (id, name, type, description, config, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                RETURNING id, name, type, description, config, metadata, created_at, updated_at
                """,
                (agent_id, name, agent_type, description,
                 psycopg.types.json.Json(config), psycopg.types.json.Json(metadata))
            )
            row = cur.fetchone()
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "config": row[4] or {},
            "metadata": row[5] or {},
            "created_at": row[6],
            "updated_at": row[7]
        }
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID."""
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, type, description, config, metadata, created_at, updated_at
                FROM agents WHERE id = %s
                """,
                (agent_id,)
            )
            row = cur.fetchone()
            
        if not row:
            return None
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "config": row[4] or {},
            "metadata": row[5] or {},
            "created_at": row[6],
            "updated_at": row[7]
        }
    
    # Sessions operations
    def create_session(self, user_id: str, agent_id: str,
                      name: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        with self.db.connect() as conn, conn.cursor() as cur:
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
            "created_at": row[5],
            "updated_at": row[6]
        }
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID with user and agent info."""
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.user_id, s.agent_id, s.name, s.metadata, 
                       s.created_at, s.updated_at, u.name as user_name, a.name as agent_name
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                JOIN agents a ON s.agent_id = a.id
                WHERE s.id = %s
                """,
                (session_id,)
            )
            row = cur.fetchone()
            
        if not row:
            return None
            
        return {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "agent_id": str(row[2]),
            "name": row[3],
            "metadata": row[4] or {},
            "created_at": row[5],
            "updated_at": row[6],
            "user_name": row[7],
            "agent_name": row[8]
        }
    
    # Messages operations
    def create_message(self, session_id: str, role: str, content: str,
                      metadata: Optional[Dict[str, Any]] = None,
                      tags: Optional[List[str]] = None,
                      workflow_id: Optional[str] = None,
                      step_index: Optional[int] = None) -> Dict[str, Any]:
        """Create a new message."""
        message_id = str(uuid.uuid4())
        metadata = metadata or {}
        tags = tags or []
        
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (id, session_id, role, content, metadata, tags, workflow_id, step_index)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                RETURNING id, session_id, role, content, metadata, tags, workflow_id, step_index, created_at
                """,
                (message_id, session_id, role, content,
                 psycopg.types.json.Json(metadata), tags, workflow_id, step_index)
            )
            row = cur.fetchone()
            
        return {
            "id": str(row[0]),
            "session_id": str(row[1]),
            "role": row[2],
            "content": row[3],
            "metadata": row[4] or {},
            "tags": row[5] or [],
            "workflow_id": str(row[6]) if row[6] else None,
            "step_index": row[7],
            "created_at": row[8]
        }
    
    def get_or_create_session_mapping(self, session_id: str) -> str:
        """Get or create mapping between new session UUID and old session string."""
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT old_session_id FROM session_mappings WHERE new_session_id = %s",
                (session_id,)
            )
            row = cur.fetchone()
            
            if row:
                return row[0]
            else:
                # Create a mapping for this session
                old_session_id = f"api_session_{session_id}"
                cur.execute(
                    """INSERT INTO session_mappings (old_session_id, new_session_id) 
                       VALUES (%s, %s)""",
                    (old_session_id, session_id)
                )
                return old_session_id
