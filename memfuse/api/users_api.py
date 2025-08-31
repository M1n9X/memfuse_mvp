"""
Users API endpoints for MemFuse.
Handles user CRUD operations and queries.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Path
import psycopg

from memfuse.db import Database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def get_db() -> Database:
    """Dependency injection placeholder - will be overridden by main app."""
    raise NotImplementedError("Database dependency not configured")


# Make get_db accessible for dependency override
router.get_db = get_db


@router.post("/", response_model=dict)
async def create_user(user_data: dict, db: Database = Depends(get_db)):
    """Create a new user."""
    try:
        name = user_data.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        
        email = user_data.get("email")
        metadata = user_data.get("metadata", {})
        
        user_id = str(uuid.uuid4())
        
        with db.connect() as conn, conn.cursor() as cur:
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
            "created_at": row[4].isoformat(),
            "updated_at": row[5].isoformat()
        }
        
    except psycopg.IntegrityError as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="User with this name already exists")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[dict])
async def list_users(
    name: Optional[str] = Query(None, description="Filter by user name"),
    limit: int = Query(50, le=1000, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    db: Database = Depends(get_db)
):
    """List users with optional filtering."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            if name:
                cur.execute(
                    """
                    SELECT id, name, email, metadata, created_at, updated_at
                    FROM users 
                    WHERE name ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (f"%{name}%", limit, offset)
                )
            else:
                cur.execute(
                    """
                    SELECT id, name, email, metadata, created_at, updated_at
                    FROM users 
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset)
                )
            
            rows = cur.fetchall()
            
        return [
            {
                "id": str(row[0]),
                "name": row[1],
                "email": row[2],
                "metadata": row[3] or {},
                "created_at": row[4].isoformat(),
                "updated_at": row[5].isoformat()
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: str = Path(..., description="User ID"),
    db: Database = Depends(get_db)
):
    """Get a specific user by ID."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, metadata, created_at, updated_at
                FROM users 
                WHERE id = %s
                """,
                (user_id,)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "metadata": row[3] or {},
            "created_at": row[4].isoformat(),
            "updated_at": row[5].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: str = Path(..., description="User ID"),
    user_data: dict = None,
    db: Database = Depends(get_db)
):
    """Update a user."""
    try:
        if not user_data:
            raise HTTPException(status_code=400, detail="Update data is required")
            
        # Build dynamic update query
        update_fields = []
        params = []
        
        if "name" in user_data:
            update_fields.append("name = %s")
            params.append(user_data["name"])
            
        if "email" in user_data:
            update_fields.append("email = %s")
            params.append(user_data["email"])
            
        if "metadata" in user_data:
            update_fields.append("metadata = %s::jsonb")
            params.append(psycopg.types.json.Json(user_data["metadata"]))
            
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        params.append(user_id)
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, name, email, metadata, created_at, updated_at
                """,
                params
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "metadata": row[3] or {},
            "created_at": row[4].isoformat(),
            "updated_at": row[5].isoformat()
        }
        
    except HTTPException:
        raise
    except psycopg.IntegrityError as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="User with this name already exists")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{user_id}")
async def delete_user(
    user_id: str = Path(..., description="User ID"),
    db: Database = Depends(get_db)
):
    """Delete a user."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-name/{name}", response_model=dict)
async def get_user_by_name(
    name: str = Path(..., description="User name"),
    db: Database = Depends(get_db)
):
    """Get a user by name."""
    try:
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, metadata, created_at, updated_at
                FROM users 
                WHERE name = %s
                """,
                (name,)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "metadata": row[3] or {},
            "created_at": row[4].isoformat(),
            "updated_at": row[5].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user by name {name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
