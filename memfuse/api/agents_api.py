"""
Agents API endpoints for MemFuse.
Handles agent CRUD operations and queries.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Path
import psycopg

from memfuse.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def get_db() -> Database:
    """Dependency injection placeholder - will be overridden by main app."""
    raise NotImplementedError("Database dependency not configured")


# Make get_db accessible for dependency override
router.get_db = get_db


@router.post("/", response_model=dict)
async def create_agent(agent_data: dict, db: Database = Depends(get_db)):
    """Create a new agent."""
    try:
        name = agent_data.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        
        agent_type = agent_data.get("type", "assistant")
        description = agent_data.get("description")
        config = agent_data.get("config", {})
        metadata = agent_data.get("metadata", {})
        
        agent_id = str(uuid.uuid4())
        
        with db.connect() as conn, conn.cursor() as cur:
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
            "created_at": row[6].isoformat(),
            "updated_at": row[7].isoformat()
        }
        
    except psycopg.IntegrityError as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Agent with this name already exists")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[dict])
async def list_agents(
    name: Optional[str] = Query(None, description="Filter by agent name"),
    agent_type: Optional[str] = Query(None, alias="type", description="Filter by agent type"),
    limit: int = Query(50, le=1000, description="Maximum number of agents to return"),
    offset: int = Query(0, ge=0, description="Number of agents to skip"),
    db: Database = Depends(get_db)
):
    """List agents with optional filtering."""
    try:
        conditions = []
        params = []
        
        if name:
            conditions.append("name ILIKE %s")
            params.append(f"%{name}%")
            
        if agent_type:
            conditions.append("type = %s")
            params.append(agent_type)
            
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
            
        params.extend([limit, offset])
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, name, type, description, config, metadata, created_at, updated_at
                FROM agents 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params
            )
            rows = cur.fetchall()
            
        return [
            {
                "id": str(row[0]),
                "name": row[1],
                "type": row[2],
                "description": row[3],
                "config": row[4] or {},
                "metadata": row[5] or {},
                "created_at": row[6].isoformat(),
                "updated_at": row[7].isoformat()
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}", response_model=dict)
async def get_agent(
    agent_id: str = Path(..., description="Agent ID"),
    db: Database = Depends(get_db)
):
    """Get a specific agent by ID."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, type, description, config, metadata, created_at, updated_at
                FROM agents 
                WHERE id = %s
                """,
                (agent_id,)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "config": row[4] or {},
            "metadata": row[5] or {},
            "created_at": row[6].isoformat(),
            "updated_at": row[7].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{agent_id}", response_model=dict)
async def update_agent(
    agent_id: str = Path(..., description="Agent ID"),
    agent_data: dict = None,
    db: Database = Depends(get_db)
):
    """Update an agent."""
    try:
        if not agent_data:
            raise HTTPException(status_code=400, detail="Update data is required")
            
        # Build dynamic update query
        update_fields = []
        params = []
        
        if "name" in agent_data:
            update_fields.append("name = %s")
            params.append(agent_data["name"])
            
        if "type" in agent_data:
            update_fields.append("type = %s")
            params.append(agent_data["type"])
            
        if "description" in agent_data:
            update_fields.append("description = %s")
            params.append(agent_data["description"])
            
        if "config" in agent_data:
            update_fields.append("config = %s::jsonb")
            params.append(psycopg.types.json.Json(agent_data["config"]))
            
        if "metadata" in agent_data:
            update_fields.append("metadata = %s::jsonb")
            params.append(psycopg.types.json.Json(agent_data["metadata"]))
            
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        params.append(agent_id)
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE agents 
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, name, type, description, config, metadata, created_at, updated_at
                """,
                params
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "config": row[4] or {},
            "metadata": row[5] or {},
            "created_at": row[6].isoformat(),
            "updated_at": row[7].isoformat()
        }
        
    except HTTPException:
        raise
    except psycopg.IntegrityError as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Agent with this name already exists")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str = Path(..., description="Agent ID"),
    db: Database = Depends(get_db)
):
    """Delete an agent."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
            
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        return {"message": "Agent deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-name/{name}", response_model=dict)
async def get_agent_by_name(
    name: str = Path(..., description="Agent name"),
    db: Database = Depends(get_db)
):
    """Get an agent by name."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, type, description, config, metadata, created_at, updated_at
                FROM agents 
                WHERE name = %s
                """,
                (name,)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "config": row[4] or {},
            "metadata": row[5] or {},
            "created_at": row[6].isoformat(),
            "updated_at": row[7].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent by name {name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
