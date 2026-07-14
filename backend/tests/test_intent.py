"""Unit tests for the shared chat-intent detection rules."""
from services.intent import (
    extract_hymn_query,
    first_name,
    has_audio_intent,
    is_explicit_random_request,
    is_greeting,
    is_how_are_you,
    is_informational,
    resolve_hymn_query,
)


def test_has_audio_intent_detects_play_words():
    assert has_audio_intent("sing me hymn 2")
    assert has_audio_intent("can you play something")
    assert not has_audio_intent("what is hymn 2")


def test_is_informational_detects_question_words():
    assert is_informational("what is hymn 2")
    assert is_informational("tell me about hymn 2")
    assert not is_informational("sing me hymn 2")


def test_extract_hymn_query_strips_filler_words():
    assert extract_hymn_query("sing me hymn 2") == "2"
    assert extract_hymn_query("play the spirit of god") == "spirit of god"


def test_extract_hymn_query_falls_back_to_full_message_without_sing_pattern():
    assert extract_hymn_query("hymn 2") == "2"


def test_resolve_hymn_query_returns_none_for_informational_message():
    assert resolve_hymn_query("what is hymn 2") is None


def test_resolve_hymn_query_returns_none_without_audio_intent():
    assert resolve_hymn_query("tell me about music theory") is None


def test_resolve_hymn_query_extracts_query_for_audio_intent():
    assert resolve_hymn_query("sing me hymn 2") == "2"


def test_is_explicit_random_request():
    assert is_explicit_random_request("play something")
    assert is_explicit_random_request("any random song")
    assert not is_explicit_random_request("hymn 2")


def test_is_greeting_short_messages_only():
    assert is_greeting("hello")
    assert is_greeting("hi there")
    # Long messages that happen to contain "hi" shouldn't count as greetings
    assert not is_greeting("hi, i wanted to ask a very long question about hymn conducting")


def test_is_how_are_you_variants():
    assert is_how_are_you("how are you")
    assert is_how_are_you("what's up")
    assert not is_how_are_you("what is a hymn")


def test_first_name_extracts_first_token():
    assert first_name("Jane Doe") == "Jane"
    assert first_name("Cher") == "Cher"


def test_first_name_handles_missing_name():
    assert first_name(None) == ""
    assert first_name("") == ""
