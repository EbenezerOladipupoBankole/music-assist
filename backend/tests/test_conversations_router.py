"""Tests for the conversation-history endpoints."""


def test_get_user_conversations_returns_empty_list_without_rag_pipeline(client_no_rag):
    response = client_no_rag.get("/conversations/user1")

    assert response.status_code == 200
    assert response.json() == []


def test_get_user_conversations_lists_conversations_after_a_chat(client):
    client.post("/chat", json={"message": "what is a hymn", "user_id": "user1", "conversation_id": "conv1"})

    response = client.get("/conversations/user1")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "conv1"


def test_get_conversation_history_formats_messages_for_frontend(client):
    client.post("/chat", json={"message": "what is a hymn", "conversation_id": "conv1"})

    response = client.get("/conversations/conv1/history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2  # one user message + one AI message
    assert body[0]["sender"] == "user"
    assert body[1]["sender"] == "ai"


def test_get_conversation_history_empty_without_rag_pipeline(client_no_rag):
    response = client_no_rag.get("/conversations/conv1/history")

    assert response.status_code == 200
    assert response.json() == []
