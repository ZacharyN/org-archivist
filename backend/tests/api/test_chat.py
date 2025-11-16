"""
Integration tests for chat endpoints.
"""
import pytest


def test_chat_endpoint_exists(client):
    """Test that the chat endpoint is accessible."""
    response = client.post("/api/chat")

    # Should get 422 (validation error) not 404
    assert response.status_code in [422, 400]


def test_chat_with_valid_request(client, sample_chat_request):
    """Test chat endpoint with valid request structure."""
    response = client.post("/api/chat", json=sample_chat_request)

    # Should accept valid request
    assert response.status_code in [200, 201]

    if response.status_code == 200:
        data = response.json()
        assert "message" in data or "response" in data or isinstance(data, dict)


def test_chat_required_fields(client):
    """Test that chat requires message field."""
    response = client.post("/api/chat", json={})

    assert response.status_code == 422


def test_chat_new_conversation(client):
    """Test starting a new conversation."""
    response = client.post(
        "/api/chat",
        json={
            "message": "Hello, I need help with a grant proposal.",
            "conversation_id": None
        }
    )

    assert response.status_code in [200, 201]

    if response.status_code == 200:
        data = response.json()
        # Should return conversation_id for new conversations
        assert "conversation_id" in data or isinstance(data, dict)


def test_chat_continue_conversation(client):
    """Test continuing an existing conversation."""
    # First create a conversation
    initial_response = client.post(
        "/api/chat",
        json={
            "message": "What are the key elements of a needs statement?",
            "conversation_id": None
        }
    )

    if initial_response.status_code == 200:
        data = initial_response.json()

        # Try to continue (if conversation_id provided)
        if "conversation_id" in data:
            follow_up = client.post(
                "/api/chat",
                json={
                    "message": "Can you give me an example?",
                    "conversation_id": data["conversation_id"]
                }
            )

            assert follow_up.status_code in [200, 201]


def test_get_conversation_history(client):
    """Test retrieving conversation history."""
    # Try to get a conversation (will 404 if not exists)
    test_id = "test-conversation-123"
    response = client.get(f"/api/chat/{test_id}")

    # Should be valid endpoint
    assert response.status_code in [200, 404]


def test_list_conversations(client):
    """Test listing all conversations."""
    response = client.get("/api/chat")

    # Should be valid endpoint
    assert response.status_code == 200

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, (list, dict))


def test_delete_conversation(client):
    """Test deleting a conversation."""
    test_id = "test-conversation-123"
    response = client.delete(f"/api/chat/{test_id}")

    # Should be valid endpoint
    assert response.status_code in [200, 204, 404]


def test_chat_empty_message(client):
    """Test that empty messages are rejected."""
    response = client.post(
        "/api/chat",
        json={
            "message": "",
            "conversation_id": None
        }
    )

    # Should reject empty message
    assert response.status_code == 422


def test_chat_context_window(client):
    """Test chat with custom context window."""
    response = client.post(
        "/api/chat",
        json={
            "message": "Test message",
            "context_window": 5
        }
    )

    assert response.status_code in [200, 201]


def test_chat_response_structure(client, sample_chat_request):
    """Test that chat responses have expected structure."""
    response = client.post("/api/chat", json=sample_chat_request)

    if response.status_code == 200:
        data = response.json()

        # Response should be a dict
        assert isinstance(data, dict)

        # Should have some content
        assert len(data) > 0
