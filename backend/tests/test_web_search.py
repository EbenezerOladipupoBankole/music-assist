"""Unit tests for the pure, no-I/O logic in web_search.py."""
from web_search import ChurchMusicWebSearch, is_music_related_question

# ---- is_music_related_question ------------------------------------------------

def test_detects_music_keywords():
    assert is_music_related_question("What hymn should we sing for the sacrament?")


def test_rejects_offtopic_query_without_history():
    assert not is_music_related_question("what is the capital of france")


def test_detects_hymn_number_pattern():
    assert is_music_related_question("what is hymn #2")


def test_allows_short_greetings():
    assert is_music_related_question("hello")


def test_allows_followup_phrasing_only_with_history():
    assert is_music_related_question("tell me more", has_history=True)
    assert not is_music_related_question("tell me more", has_history=False)


def test_detects_hymn_history_question():
    assert is_music_related_question("who composed this melody")


# ---- ChurchMusicWebSearch._is_relevant / _calculate_relevance -----------------

def test_is_relevant_true_when_multiple_terms_match():
    searcher = ChurchMusicWebSearch()
    assert searcher._is_relevant("The ward choir needs a new conductor", "ward choir conductor")


def test_is_relevant_false_when_terms_dont_match():
    searcher = ChurchMusicWebSearch()
    assert not searcher._is_relevant("completely unrelated content here", "ward choir conductor")


def test_calculate_relevance_rewards_higher_term_density():
    searcher = ChurchMusicWebSearch()
    dense = searcher._calculate_relevance("hymn hymn hymn hymn hymn", "hymn")
    sparse = searcher._calculate_relevance("hymn " + "filler " * 50, "hymn")
    assert dense > sparse


def test_calculate_relevance_caps_at_one():
    searcher = ChurchMusicWebSearch()
    # Raw density here is 5 / (5/10) = 10.0 - the cap is what keeps it at 1.0.
    assert searcher._calculate_relevance("hymn hymn hymn hymn hymn", "hymn") == 1.0
