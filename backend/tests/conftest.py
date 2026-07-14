"""
Shared pytest fixtures for the backend test suite.

Router tests use FastAPI's `dependency_overrides` plus a plain (NOT
context-managed) `TestClient`, so the real `lifespan` - which needs a live
OPENAI_API_KEY and talks to OpenAI/FAISS - never runs. Only `scope["type"] ==
"http"` traffic is exercised, which doesn't depend on lifespan having fired,
so the whole suite runs offline with no API key.
"""
import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple

# RAGPipeline.__init__ requires OPENAI_API_KEY to be present (it never has to be
# *valid* here - nothing in this suite makes a real network call). Set a dummy
# value before anything imports rag_pipeline so the whole suite runs offline.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

import pytest
from fastapi.testclient import TestClient

from dependencies import (
    get_audio_cache,
    get_hymn_player,
    get_rag_pipeline,
    get_rag_pipeline_optional,
)
from hymn_player import HymnPlayer
from main import app


class FakeMemory:
    """In-memory stand-in for SQLiteConversationMemory / FirebaseConversationMemory."""

    def __init__(self):
        self._messages: Dict[str, List[Tuple[str, str]]] = {}
        self._meta: Dict[str, dict] = {}

    def get_history(self, conversation_id: str) -> List[Tuple[str, str]]:
        return list(self._messages.get(conversation_id, []))

    def add_message(
        self,
        conversation_id: str,
        user_query: str,
        ai_response: str,
        user_id: Optional[str] = None,
    ) -> None:
        self._messages.setdefault(conversation_id, []).append((user_query, ai_response))
        existing_title = self._meta.get(conversation_id, {}).get("title")
        self._meta[conversation_id] = {
            "id": conversation_id,
            "title": existing_title or user_query[:50],
            "last_updated": 0,
            "user_id": user_id,
        }

    def get_user_conversations(self, user_id: str) -> List[dict]:
        return [m for m in self._meta.values() if m.get("user_id") == user_id]


class FakeRAGPipeline:
    """Stand-in for RAGPipeline that never touches OpenAI/FAISS."""

    def __init__(self, answer: str = "The mocked answer.", healthy: bool = True):
        self.memory = FakeMemory()
        self.answer = answer
        self.healthy = healthy

    async def query(self, query: str, conversation_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        cid = conversation_id or "conv_fake"
        await asyncio.to_thread(self.memory.add_message, cid, query, self.answer, user_id)
        return {
            "answer": self.answer,
            "sources": [],
            "conversation_id": cid,
            "confidence": "high",
            "search_method": "local only",
        }

    async def stream_query(self, query: str, conversation_id: Optional[str], user_id: Optional[str]):
        cid = conversation_id or "conv_fake"
        yield json.dumps({"type": "metadata", "sources": [], "confidence": "high", "conversation_id": cid})
        yield json.dumps({"type": "content", "delta": self.answer})
        await asyncio.to_thread(self.memory.add_message, cid, query, self.answer, user_id)

    async def health_check(self) -> dict:
        return {"status": "healthy" if self.healthy else "unhealthy", "checks": {}}

    async def get_stats(self) -> dict:
        return {"status": "healthy", "total_queries": 0}


class FakeAudioCache:
    """Always misses, forcing the direct-proxy fallback path in tests."""

    def get_local_path(self, hymn_number: int, source_url: Optional[str]) -> Optional[str]:
        return None


@pytest.fixture
def fake_rag_pipeline() -> FakeRAGPipeline:
    return FakeRAGPipeline()


@pytest.fixture
def client(fake_rag_pipeline):
    """A TestClient wired to the real routers with heavy dependencies faked out."""
    app.dependency_overrides[get_rag_pipeline] = lambda: fake_rag_pipeline
    app.dependency_overrides[get_rag_pipeline_optional] = lambda: fake_rag_pipeline
    app.dependency_overrides[get_hymn_player] = lambda: HymnPlayer()
    app.dependency_overrides[get_audio_cache] = lambda: FakeAudioCache()

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client_no_rag():
    """A TestClient where the RAG pipeline is unavailable (init failed / still booting)."""
    app.dependency_overrides[get_rag_pipeline_optional] = lambda: None
    app.dependency_overrides[get_hymn_player] = lambda: HymnPlayer()

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
