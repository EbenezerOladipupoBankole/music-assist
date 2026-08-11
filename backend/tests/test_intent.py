"""Unit tests for the shared chat-intent detection rules."""
from services.intent import (
    first_name,
    is_greeting,
    is_how_are_you,
)


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
