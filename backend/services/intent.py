"""
Lightweight, regex-based intent detection for the chat endpoints.

This logic used to be duplicated verbatim between /chat and /chat/stream in
main.py. Pulling it out means the two endpoints can't drift apart, and the
detection rules themselves become unit-testable without spinning up FastAPI.
"""
from typing import Optional

INFORMATIONAL_WORDS = ["list", "about", "what is", "how many", "tell me", "explain"]
RANDOM_REQUEST_WORDS = ["random", "something", "any song"]

GREETING_WORDS = [
    "hello", "hi", "hey", "greetings",
    "good morning", "good afternoon", "good evening", "howdy",
]
HOW_ARE_YOU_PATTERNS = [
    "how are you", "how are u", "how r you", "how r u",
    "how's it going", "how is it going", "what's up", "whats up",
]




def is_explicit_random_request(query: str) -> bool:
    return any(word in query.lower() for word in RANDOM_REQUEST_WORDS)


def is_greeting(user_msg: str) -> bool:
    return any(greeting in user_msg for greeting in GREETING_WORDS) and len(user_msg) < 20


def is_how_are_you(user_msg: str) -> bool:
    return any(pattern in user_msg for pattern in HOW_ARE_YOU_PATTERNS)


def first_name(user_name: Optional[str]) -> str:
    """First token of a display name, or '' if none was given."""
    if not user_name:
        return ""
    return user_name.split()[0]
