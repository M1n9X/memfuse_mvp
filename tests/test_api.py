"""
Tests for MemFuse API endpoints.
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from memfuse.api_server import app, override_dependencies
from memfuse.db import DatabaseManager
from memfuse.rag import RAGPipeline
from memfuse.orchestrator import Orchestrator


@pytest.fixture
def mock_db():
    """Mock database manager."""
    return Mock(spec=DatabaseManager)


@pytest.fixture
def mock_rag():
    """Mock RAG pipeline."""
    return Mock(spec=RAGPipeline)


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    return Mock(spec=Orchestrator)


@pytest.fixture
def client(mock_db, mock_rag, mock_orchestrator):
    """Test client with mocked dependencies."""
    
    def get_mock_db():
        return mock_db
    
    def get_mock_rag():
        return mock_rag
    
    def get_mock_orchestrator():
        return mock_orchestrator
    
    # Override dependencies
    from memfuse.api.users_api import router as users_router
    from memfuse.api.agents_api import router as agents_router
    from memfuse.api.sessions_api import router as sessions_router
    from memfuse.api.messages_api import router as messages_router
    
    users_router.dependency_overrides[users_router.get_db] = get_mock_db
    agents_router.dependency_overrides[agents_router.get_db] = get_mock_db
    sessions_router.dependency_overrides[sessions_router.get_db] = get_mock_db
    messages_router.dependency_overrides[messages_router.get_db] = get_mock_db
    messages_router.dependency_overrides[messages_router.get_rag] = get_mock_rag
    messages_router.dependency_overrides[messages_router.get_orchestrator] = get_mock_orchestrator
    
    return TestClient(app)


class TestUsersAPI:
    """Test users API endpoints."""
    
    def test_create_user(self, client, mock_db):
        """Test user creation."""
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (
            "user-123", "test_user", "test@example.com", {}, 
            "2023-01-01T00:00:00", "2023-01-01T00:00:00"
        )
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.post("/users/", json={
            "name": "test_user",
            "email": "test@example.com"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_user"
        assert data["email"] == "test@example.com"
    
    def test_get_user_by_id(self, client, mock_db):
        """Test getting user by ID."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (
            "user-123", "test_user", "test@example.com", {},
            "2023-01-01T00:00:00", "2023-01-01T00:00:00"
        )
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.get("/users/user-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user-123"
        assert data["name"] == "test_user"
    
    def test_get_user_not_found(self, client, mock_db):
        """Test getting non-existent user."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.get("/users/nonexistent")
        
        assert response.status_code == 404


class TestAgentsAPI:
    """Test agents API endpoints."""
    
    def test_create_agent(self, client, mock_db):
        """Test agent creation."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (
            "agent-123", "test_agent", "assistant", "Test agent", {}, {},
            "2023-01-01T00:00:00", "2023-01-01T00:00:00"
        )
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.post("/agents/", json={
            "name": "test_agent",
            "type": "assistant",
            "description": "Test agent"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_agent"
        assert data["type"] == "assistant"


class TestSessionsAPI:
    """Test sessions API endpoints."""
    
    def test_create_session(self, client, mock_db):
        """Test session creation."""
        mock_cursor = Mock()
        # Mock user and agent existence checks
        mock_cursor.fetchone.side_effect = [
            ("user-123",),  # User exists
            ("agent-123",),  # Agent exists
            ("session-123", "user-123", "agent-123", "Test Session", {},
             "2023-01-01T00:00:00", "2023-01-01T00:00:00")  # Created session
        ]
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.post("/sessions/", json={
            "user_id": "user-123",
            "agent_id": "agent-123",
            "name": "Test Session"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["agent_id"] == "agent-123"


class TestMessagesAPI:
    """Test messages API endpoints."""
    
    def test_create_message(self, client, mock_db):
        """Test message creation."""
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            ("session-123",),  # Session exists
            ("msg-123", "session-123", "user", "Hello", {}, [], None, None, "2023-01-01T00:00:00")
        ]
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.post("/sessions/session-123/messages", json={
            "role": "user",
            "content": "Hello"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello"
    
    def test_chat_endpoint(self, client, mock_db, mock_rag):
        """Test chat endpoint."""
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            ("session-123",),  # Session exists
            None,  # No existing mapping
            ("msg-123", "session-123", "assistant", "Hello back!", {}, [], None, "2023-01-01T00:00:00")
        ]
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_rag.generate_response.return_value = "Hello back!"
        
        response = client.post("/sessions/session-123/chat", json={
            "content": "Hello",
            "enable_m3": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello back!"


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client, mock_db):
        """Test health check."""
        mock_cursor = Mock()
        mock_db.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MemFuse API"
        assert "endpoints" in data
