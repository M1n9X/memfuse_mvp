"""
FastAPI server for MemFuse API endpoints.
Provides RESTful API for users, agents, sessions, and messages management.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from memfuse.config import Settings
from memfuse.db import Database
from memfuse.rag import RAGService
from memfuse.orchestrator import Orchestrator
from memfuse.api_db import APIDatabase
from memfuse.api.users_api import router as users_router
from memfuse.api.agents_api import router as agents_router
from memfuse.api.sessions_api import router as sessions_router
from memfuse.api.messages_api import router as messages_router
from .api.query_api import router as query_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db_manager: Optional[Database] = None
rag_pipeline: Optional[RAGService] = None
orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global db_manager, rag_pipeline, orchestrator

    try:
        settings = Settings.from_env()

        # Initialize database
        db_manager = Database.from_settings(settings)
        logger.info("Database manager initialized")

        # Initialize RAG pipeline
        rag_pipeline = RAGService.from_settings(settings)
        logger.info("RAG pipeline initialized")

        # Initialize orchestrator for complex tasks
        orchestrator = Orchestrator.from_settings(settings)
        logger.info("Orchestrator initialized")

        # Configure dependency injection after initialization
        override_dependencies()
        logger.info("Dependencies configured")

        yield

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        # Cleanup if needed
        logger.info("Shutting down services")


# Create FastAPI app
app = FastAPI(
    title="MemFuse API",
    description=(
        "API for MemFuse - AI system with layered memory "
        "and multi-agent capabilities"
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure dependency injection for API routers


def override_dependencies():
    """Override dependencies in API routers with actual instances."""
    # Use app-level dependency overrides instead of router-level
    app.dependency_overrides[users_router.get_db] = get_db
    app.dependency_overrides[agents_router.get_db] = get_db
    app.dependency_overrides[sessions_router.get_db] = get_db
    app.dependency_overrides[messages_router.get_db] = get_db
    app.dependency_overrides[messages_router.get_rag] = get_rag
    app.dependency_overrides[
        messages_router.get_orchestrator
    ] = get_orchestrator
    app.dependency_overrides[query_router.get_db] = get_db
    app.dependency_overrides[query_router.get_rag] = get_rag


# Register API routers
app.include_router(users_router)
app.include_router(agents_router)
app.include_router(sessions_router)
app.include_router(messages_router)
app.include_router(query_router)


# Dependency to get database manager
def get_db() -> Database:
    if db_manager is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_manager


def get_rag() -> RAGService:
    if rag_pipeline is None:
        raise HTTPException(
            status_code=500, detail="RAG pipeline not initialized"
        )
    return rag_pipeline


def get_orchestrator() -> Orchestrator:
    if orchestrator is None:
        raise HTTPException(
            status_code=500, detail="Orchestrator not initialized"
        )
    return orchestrator


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        # Simple database connectivity check
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": "connected",
                "rag_pipeline": (
                    "initialized" if rag_pipeline else "not_initialized"
                ),
                "orchestrator": (
                    "initialized" if orchestrator else "not_initialized"
                )
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, detail=f"Service unhealthy: {str(e)}"
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "MemFuse API",
        "version": "1.0.0",
        "description": (
            "API for MemFuse - AI system with layered memory "
            "and multi-agent capabilities"
        ),
        "endpoints": {
            "users": "/users",
            "agents": "/agents",
            "sessions": "/sessions",
            "messages": "/sessions/{session_id}/messages",
            "chat": "/sessions/{session_id}/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "memfuse.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
