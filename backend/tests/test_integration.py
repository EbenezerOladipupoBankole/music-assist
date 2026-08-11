"""
Integration tests for the RAGPipeline — Tests A through F from the audit report.

These tests use pytest-asyncio and unittest.mock to drive the *real*
RAGPipeline object with faked external I/O (LLM, FAISS, web search, memory),
so that each test catches a genuine regression in production logic rather than
asserting on stub behaviour.

Run with:
    pytest tests/test_integration.py -v -s
"""
import os
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# The dummy key must be set before rag_pipeline is imported.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

from rag_pipeline import RAGPipeline  # noqa: E402

# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

def _make_pipeline() -> RAGPipeline:
    """Return a RAGPipeline whose LLM and embeddings are mocked so no network
    calls are ever made.  The vector_store is left None (not ._ready) by default;
    individual tests can inject a fake one where required."""
    with (
        patch("rag_pipeline.OpenAIEmbeddings"),
        patch("rag_pipeline.ChatOpenAI"),
    ):
        pipeline = RAGPipeline(
            vector_db_path="./unused-in-tests",
            model_name="gpt-4o-mini",
        )
    return pipeline


def _fake_memory(history: Optional[List] = None) -> MagicMock:
    mem = MagicMock()
    mem.get_history.return_value = history or []
    mem.add_message.return_value = None
    return mem


# ---------------------------------------------------------------------------
# Test A — Response cache: hit and miss
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_miss_then_hit_skips_llm():
    """
    Sending the exact same query twice must:
      1. Call the LLM exactly once (not twice).
      2. Return cache_hit=True on the second call.

    Regression: if _response_cache key generation changes (e.g. case
    sensitivity), every query would bypass the cache and double LLM costs.
    """
    pipeline = _make_pipeline()
    pipeline.memory = _fake_memory()
    pipeline._ready = True

    # Fake local retrieval (no real Firestore)
    pipeline.vector_store = MagicMock()
    fake_doc = MagicMock()
    fake_doc.page_content = "x" * 900
    fake_doc.metadata = {"source": "local", "title": "Hymn 1"}
    pipeline.vector_store.as_retriever.return_value.invoke.return_value = [fake_doc]

    # The LLM's synchronous invoke is called inside asyncio.to_thread
    llm_mock = MagicMock(return_value=MagicMock(content="William Clayton wrote it."))
    pipeline.llm.invoke = llm_mock

    # Also stub web-searcher so it never hits the network
    pipeline.web_searcher = MagicMock()
    pipeline.web_searcher.search = AsyncMock(return_value=[])

    query = "Who wrote Come Come Ye Saints"

    # --- First call (cache MISS) ---
    result1 = await pipeline.query(query, conversation_id="conv-a")
    assert result1["metrics"]["cache_hit"] is False
    assert llm_mock.call_count == 1

    # --- Second identical call (cache HIT) ---
    result2 = await pipeline.query(query, conversation_id="conv-b")
    assert result2["metrics"]["cache_hit"] is True
    # LLM should still have been called only once total
    assert llm_mock.call_count == 1, "LLM was invoked on cache hit — cache is broken"
    assert result2["answer"] == result1["answer"]


# ---------------------------------------------------------------------------
# Test B — LLM retry on transient failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generates_answer_after_transient_llm_failure():
    """
    _generate_answer() must retry on rate-limit / timeout errors and succeed
    on the 3rd attempt.  Validates that the retry loop is active and that
    exponential-backoff sleep is triggered (we patch asyncio.sleep so the test
    doesn't actually wait).

    Regression: removing the retry loop or changing the error string check
    would cause production queries to fail permanently on transient OpenAI 429s.
    """
    pipeline = _make_pipeline()
    pipeline.memory = _fake_memory()

    call_count = 0

    def flaky_invoke(_prompt: str) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("rate_limit exceeded, try again")
        return MagicMock(content="Success on 3rd attempt")

    pipeline.llm.invoke = flaky_invoke

    with patch("rag_pipeline.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await pipeline._generate_answer(
            "who wrote hymn 1", "some context about the hymn", ""
        )

    assert result == "Success on 3rd attempt"
    assert call_count == 3, f"Expected 3 LLM calls, got {call_count}"
    # At least one backoff sleep must have been triggered (on the first 2 failures)
    assert mock_sleep.await_count >= 1, "Retry backoff sleep was never called"


# ---------------------------------------------------------------------------
# Test C — Startup with missing Firestore index + failing placeholder creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialize_sets_not_ready_when_firestore_fails():
    """
    When initialization of the FirestoreVectorStore fails (e.g. bad API key),
    _ready must be False and no exception must escape initialize().

    Regression: if the inner `try/except` around FirestoreVectorStore is removed,
    a bad API key during CI would crash the entire lifespan startup.
    """
    pipeline = _make_pipeline()
    pipeline.memory = _fake_memory()

    with patch("rag_pipeline.FirestoreVectorStore", side_effect=RuntimeError("no api key")):
        await pipeline.initialize()

    assert pipeline._ready is False
    assert pipeline.vector_store is None


# ---------------------------------------------------------------------------
# Test D — Invalid / oversized input rejected at the sanitizer level
# ---------------------------------------------------------------------------

def test_validate_and_sanitize_rejects_input_over_1000_chars_truncates():
    """
    _validate_and_sanitize_input must silently truncate inputs longer than
    1000 chars (not raise), because the Pydantic schema already rejects
    >1000 at the HTTP boundary; the pipeline truncation is a defence-in-depth
    safeguard for direct/internal callers.
    """
    pipeline = _make_pipeline()
    long_input = "a" * 1500
    result = pipeline._validate_and_sanitize_input(long_input)
    assert len(result) == 1000


def test_validate_and_sanitize_rejects_too_short():
    """Any input shorter than 3 chars must raise ValueError."""
    pipeline = _make_pipeline()
    with pytest.raises(ValueError, match="too short"):
        pipeline._validate_and_sanitize_input("hi")


def test_validate_and_sanitize_strips_null_bytes():
    """Null bytes must be stripped to prevent log-injection / prompt attacks."""
    pipeline = _make_pipeline()
    result = pipeline._validate_and_sanitize_input("hello\x00world")
    assert "\x00" not in result


# ---------------------------------------------------------------------------
# Test E — Rate limit enforcement (HTTP router level via TestClient)
# ---------------------------------------------------------------------------
# NOTE: slowapi by default keys on IP.  TestClient sends requests from
# 127.0.0.1, so we need to reset the limiter state between test runs.
# The cleanest approach is to patch the limiter to always allow N-1 and
# then fail on N, which avoids time-based flakiness.

def test_chat_rate_limit_returns_429_on_throttle(client):
    """
    Sending more requests than the rate-limit allows must eventually
    receive HTTP 429 Too Many Requests.

    We use the greeting "hello" which short-circuits to a canned response
    (no LLM call), so each request completes instantly.

    Regression: if the @limiter.limit() decorator is removed from the route
    the endpoint is unprotected and every request will return 200.
    """
    got_429 = False
    for i in range(25):
        response = client.post("/chat", json={"message": "hello"})
        if response.status_code == 429:
            got_429 = True
            break

    assert got_429, (
        f"Expected HTTP 429 after exceeding rate limit, but all {i + 1} "
        f"requests returned status {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Test F — Off-topic rejection flows through the full query() path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_returns_off_topic_response_for_non_music_input():
    """
    Sending an unambiguously off-topic question must return 'off-topic' as the
    search_method and must NOT call the LLM or vector store at all.

    Regression: if `is_music_related_question` is accidentally removed from
    query(), off-topic questions would hit the LLM and consume API tokens /
    return nonsense answers.
    """
    pipeline = _make_pipeline()
    pipeline.memory = _fake_memory()
    pipeline._ready = True

    llm_mock = MagicMock()
    pipeline.llm.invoke = llm_mock

    result = await pipeline.query(
        "what is the capital of France",
        conversation_id="conv-offtopic",
    )

    assert result["search_method"] == "off-topic"
    assert "music" in result["answer"].lower() or "hymn" in result["answer"].lower(), (
        "Off-topic response did not redirect user to music domain"
    )
    # LLM must NOT have been called
    llm_mock.assert_not_called()
