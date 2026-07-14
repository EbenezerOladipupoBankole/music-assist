"""
Unit tests for RAGPipeline's pure-ish helper methods - the parts of the
pipeline that don't require a live OpenAI call or a real FAISS index.
"""
import pytest
from langchain_core.documents import Document

from rag_pipeline import RAGPipeline


@pytest.fixture
def pipeline():
    # vector_db_path is never touched by the methods under test here.
    return RAGPipeline(vector_db_path="./unused-in-tests", model_name="gpt-4o-mini")


# ---- _validate_and_sanitize_input -----------------------------------------

def test_validate_and_sanitize_strips_whitespace(pipeline):
    assert pipeline._validate_and_sanitize_input("  hello there  ") == "hello there"


def test_validate_and_sanitize_rejects_empty_string(pipeline):
    with pytest.raises(ValueError):
        pipeline._validate_and_sanitize_input("")


def test_validate_and_sanitize_rejects_too_short(pipeline):
    with pytest.raises(ValueError):
        pipeline._validate_and_sanitize_input("hi")


def test_validate_and_sanitize_truncates_long_input(pipeline):
    result = pipeline._validate_and_sanitize_input("a" * 2000)
    assert len(result) == 1000


def test_validate_and_sanitize_collapses_whitespace(pipeline):
    assert pipeline._validate_and_sanitize_input("hello    there\n\nfriend") == "hello there friend"


def test_validate_and_sanitize_strips_null_bytes(pipeline):
    assert "\x00" not in pipeline._validate_and_sanitize_input("hello\x00world")


def test_validate_and_sanitize_rejects_non_string(pipeline):
    with pytest.raises(ValueError):
        pipeline._validate_and_sanitize_input(None)


# ---- _extract_music_context -------------------------------------------------

def test_extract_music_context_finds_hymn_number(pipeline):
    context = pipeline._extract_music_context("what is hymn 193")
    assert context["hymn_numbers"] == [193]


def test_extract_music_context_ignores_out_of_range_hymn_number(pipeline):
    # The hymn book only goes up to 341; "999" is matched by the regex but
    # filtered out of the resulting list rather than being reported as real.
    context = pipeline._extract_music_context("what is hymn 999")
    assert context["hymn_numbers"] == []


def test_extract_music_context_finds_theory_terms(pipeline):
    context = pipeline._extract_music_context("explain crescendo and forte")
    assert "crescendo" in context["theory_terms"]
    assert "forte" in context["theory_terms"]


def test_extract_music_context_finds_callings(pipeline):
    context = pipeline._extract_music_context("what does a ward organist do")
    assert "organist" in context["callings"]


def test_extract_music_context_returns_none_when_nothing_found(pipeline):
    assert pipeline._extract_music_context("hello world") is None


# ---- _should_search_web ------------------------------------------------------

def test_should_search_web_true_when_no_local_docs(pipeline):
    assert pipeline._should_search_web("some query", []) is True


def test_should_search_web_false_for_substantial_local_docs(pipeline):
    docs = [Document(page_content="x" * 800, metadata={})]
    assert pipeline._should_search_web("what is a hymn", docs) is False


def test_should_search_web_true_for_short_local_docs(pipeline):
    docs = [Document(page_content="short", metadata={})]
    assert pipeline._should_search_web("what is a hymn", docs) is True


def test_should_search_web_true_for_biography_queries(pipeline):
    docs = [Document(page_content="x" * 800, metadata={})]
    assert pipeline._should_search_web("who is the composer of this hymn", docs) is True


# ---- _calculate_confidence ---------------------------------------------------

def test_calculate_confidence_high_with_strong_local_docs(pipeline):
    docs = [Document(page_content="x" * 800, metadata={}) for _ in range(3)]
    assert pipeline._calculate_confidence(docs, [], "what is a hymn") == "high"


def test_calculate_confidence_low_with_no_sources(pipeline):
    assert pipeline._calculate_confidence([], [], "what is a hymn") == "low"


def test_calculate_confidence_medium_with_web_fallback(pipeline):
    docs = [Document(page_content="short", metadata={})]
    web_results = [{"title": "a", "url": "http://x", "content": "y"}]
    assert pipeline._calculate_confidence(docs, web_results, "what is a hymn") == "medium"


# ---- _combine_contexts --------------------------------------------------------

def test_combine_contexts_includes_local_docs(pipeline):
    docs = [Document(page_content="Local content here", metadata={"title": "Hymn 1", "source": "local"})]
    combined = pipeline._combine_contexts(docs, [])
    assert "Local content here" in combined
    assert "LOCAL KNOWLEDGE BASE" in combined


def test_combine_contexts_includes_web_results(pipeline):
    web_results = [{"title": "Web Page", "url": "http://example.com", "content": "Web content here"}]
    combined = pipeline._combine_contexts([], web_results)
    assert "Web content here" in combined
    assert "CHURCH WEBSITES" in combined


def test_combine_contexts_empty_when_no_sources(pipeline):
    assert pipeline._combine_contexts([], []) == ""
