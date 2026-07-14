"""
Lightweight, regex-based intent detection for the chat endpoints.

This logic used to be duplicated verbatim between /chat and /chat/stream in
main.py. Pulling it out means the two endpoints can't drift apart, and the
detection rules themselves become unit-testable without spinning up FastAPI.
"""
import re
from typing import Optional

_SING_PATTERN = re.compile(r"\b(sing|play|listen|hear|music for|plat|plsy)\b\s*(.*)")
_FILLER_WORDS = re.compile(r"\b(me|to|a|the|hymn|song|number)\b")

AUDIO_INTENT_WORDS = ["play", "sing", "listen", "audio", "recording", "plat", "plsy"]
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


def has_audio_intent(user_msg: str) -> bool:
    """Does the message look like a request to hear/play a hymn?"""
    return any(word in user_msg for word in AUDIO_INTENT_WORDS)


def is_informational(user_msg: str) -> bool:
    """Is the message asking *about* music rather than asking to play it?"""
    return any(word in user_msg for word in INFORMATIONAL_WORDS)


def extract_hymn_query(user_msg: str) -> str:
    """Pull the hymn name/number out of a request like 'sing me hymn 2'."""
    match = _SING_PATTERN.search(user_msg)
    query = match.group(2).strip() if match else user_msg
    return _FILLER_WORDS.sub("", query).strip()


def resolve_hymn_query(user_msg: str) -> Optional[str]:
    """Return the hymn search query if this message has audio intent, else None."""
    if has_audio_intent(user_msg) and not is_informational(user_msg):
        return extract_hymn_query(user_msg)
    return None


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
