"""
Integration tests for /chat and /chat/stream, exercised through FastAPI's
TestClient with the RAG pipeline faked out (see conftest.py).

Off-topic-question filtering lives inside RAGPipeline.query() itself (not the
router), so it isn't re-tested here — see test_rag_pipeline_helpers.py and
web_search.py's own logic for that coverage.
"""
import json


def test_chat_greeting_returns_canned_response(client):
    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert "Music-Assist" in body["response"]
    assert body["sources"] == []


def test_chat_greeting_uses_first_name_when_provided(client):
    response = client.post("/chat", json={"message": "hi", "user_name": "Jane Doe"})

    assert "Jane" in response.json()["response"]


def test_chat_how_are_you_returns_canned_response(client):
    response = client.post("/chat", json={"message": "how are you"})

    assert response.status_code == 200
    assert "doing well" in response.json()["response"]


def test_chat_falls_through_to_rag_pipeline_for_standard_query(client, fake_rag_pipeline):
    response = client.post("/chat", json={"message": "what does the general handbook say about hymn selection"})

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == fake_rag_pipeline.answer
    assert body["confidence"] == "high"
    assert body["search_method"] == "local only"





def test_chat_returns_503_when_rag_pipeline_unavailable(client_no_rag):
    response = client_no_rag.post("/chat", json={"message": "what is the general handbook policy on hymns"})

    assert response.status_code == 503


def test_chat_stream_returns_503_when_rag_pipeline_unavailable(client_no_rag):
    response = client_no_rag.post("/chat/stream", json={"message": "what is a hymn"})

    assert response.status_code == 503


def test_chat_stream_yields_metadata_and_content_chunks(client, fake_rag_pipeline):
    with client.stream("POST", "/chat/stream", json={"message": "what is a hymn"}) as response:
        assert response.status_code == 200
        chunks = [json.loads(line) for line in response.iter_lines() if line.strip()]

    types = [c["type"] for c in chunks]
    assert "metadata" in types
    assert "content" in types
    content_chunk = next(c for c in chunks if c["type"] == "content")
    assert content_chunk["delta"] == fake_rag_pipeline.answer


def test_chat_stream_greeting_short_circuits_rag(client, fake_rag_pipeline):
    """Regression test: /chat/stream used to only check hymn-audio intent and
    fell through to the RAG pipeline for every greeting, since it never called
    is_greeting/is_how_are_you the way the non-streaming /chat endpoint does -
    caught by manually driving the app in a browser, not by this suite."""
    with client.stream("POST", "/chat/stream", json={"message": "hello"}) as response:
        assert response.status_code == 200
        chunks = [json.loads(line) for line in response.iter_lines() if line.strip()]

    content_chunk = next(c for c in chunks if c["type"] == "content")
    assert "Music-Assist" in content_chunk["delta"]
    assert content_chunk["delta"] != fake_rag_pipeline.answer


def test_chat_stream_how_are_you_short_circuits_rag(client, fake_rag_pipeline):
    with client.stream("POST", "/chat/stream", json={"message": "how are you"}) as response:
        assert response.status_code == 200
        chunks = [json.loads(line) for line in response.iter_lines() if line.strip()]

    content_chunk = next(c for c in chunks if c["type"] == "content")
    assert "doing well" in content_chunk["delta"]
    assert content_chunk["delta"] != fake_rag_pipeline.answer
