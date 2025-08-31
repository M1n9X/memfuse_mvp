#!/usr/bin/env python3
"""
Simple API test to verify core functionality.
"""

import requests
import time
import uuid


def test_api_endpoints():
    """Test core API endpoints."""
    base_url = "http://localhost:8001"
    
    print("🧪 Testing MemFuse API Core Functionality")
    print("=" * 50)
    
    try:
        # 1. Health check
        print("\n1. Health Check")
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        health = response.json()
        print(f"✅ API Status: {health['status']}")
        
        # 2. Create unique user
        print("\n2. Creating User")
        unique_suffix = str(int(time.time()))
        user_data = {
            "name": f"test_user_{unique_suffix}",
            "email": f"test_{unique_suffix}@memfuse.ai",
            "metadata": {"test": True}
        }
        response = requests.post(f"{base_url}/users/", json=user_data)
        assert response.status_code == 200
        user = response.json()
        print(f"✅ User created: {user['name']} (ID: {user['id']})")
        
        # 3. Create unique agent
        print("\n3. Creating Agent")
        agent_data = {
            "name": f"test_agent_{unique_suffix}",
            "type": "assistant",
            "description": "Test agent",
            "config": {"model": "gpt-4o-mini"}
        }
        response = requests.post(f"{base_url}/agents/", json=agent_data)
        assert response.status_code == 200
        agent = response.json()
        print(f"✅ Agent created: {agent['name']} (ID: {agent['id']})")
        
        # 4. Create session
        print("\n4. Creating Session")
        session_data = {
            "user_id": user["id"],
            "agent_id": agent["id"],
            "name": f"Test Session {unique_suffix}"
        }
        response = requests.post(f"{base_url}/sessions/", json=session_data)
        assert response.status_code == 200
        session = response.json()
        print(f"✅ Session created: {session['name']} (ID: {session['id']})")
        
        # 5. Basic chat
        print("\n5. Basic Chat")
        chat_data = {
            "content": "What is 2+2?",
            "enable_m3": False
        }
        response = requests.post(f"{base_url}/sessions/{session['id']}/chat", json=chat_data)
        assert response.status_code == 200
        chat_response = response.json()
        print(f"✅ Chat response: {chat_response['content'][:50]}...")
        
        # 6. List messages
        print("\n6. Listing Messages")
        response = requests.get(f"{base_url}/sessions/{session['id']}/messages")
        assert response.status_code == 200
        messages = response.json()
        print(f"✅ Found {len(messages)} messages")
        
        # 7. Get specific user
        print("\n7. Getting User by ID")
        response = requests.get(f"{base_url}/users/{user['id']}")
        assert response.status_code == 200
        retrieved_user = response.json()
        print(f"✅ Retrieved user: {retrieved_user['name']}")
        
        # 8. Get specific agent
        print("\n8. Getting Agent by ID")
        response = requests.get(f"{base_url}/agents/{agent['id']}")
        assert response.status_code == 200
        retrieved_agent = response.json()
        print(f"✅ Retrieved agent: {retrieved_agent['name']}")
        
        # 9. Get specific session
        print("\n9. Getting Session by ID")
        response = requests.get(f"{base_url}/sessions/{session['id']}")
        assert response.status_code == 200
        retrieved_session = response.json()
        print(f"✅ Retrieved session: {retrieved_session['name']}")
        
        print("\n🎉 All core API tests passed!")
        print(f"Session ID for further testing: {session['id']}")
        
        return {
            "user_id": user["id"],
            "agent_id": agent["id"],
            "session_id": session["id"]
        }
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


def test_api_docs():
    """Test API documentation endpoint."""
    print("\n📖 Testing API Documentation")
    print("-" * 30)
    
    try:
        response = requests.get("http://localhost:8001/docs")
        assert response.status_code == 200
        print("✅ API documentation accessible")
        
        response = requests.get("http://localhost:8001/openapi.json")
        assert response.status_code == 200
        openapi_spec = response.json()
        print(f"✅ OpenAPI spec available (version: {openapi_spec.get('openapi', 'unknown')})")
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")


def main():
    """Run simple API tests."""
    try:
        resource_ids = test_api_endpoints()
        test_api_docs()
        
        print("\n🎉 MemFuse API is working correctly!")
        print("\nNext steps:")
        print("1. Open API docs: http://localhost:8001/docs")
        print("2. Try M3 complex tasks (may take longer)")
        print("3. Integrate with your applications")
        
    except Exception as e:
        print(f"\n❌ API tests failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
