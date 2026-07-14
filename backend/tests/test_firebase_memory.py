"""
Unit tests for FirebaseConversationMemory's in-memory fallback path.

The fallback (self.db is None) is the part of this module that's actually
exercisable in CI/local dev, since constructing a real Firestore client needs
live Google Cloud credentials this repo doesn't ship. Instances are built via
__new__ to skip __init__ (which would try to reach Firestore) and left in the
same state __init__'s except-branch leaves them in when Firebase init fails.
"""
from firebase_memory import MAX_CONVERSATION_HISTORY, FirebaseConversationMemory


def make_fallback_memory() -> FirebaseConversationMemory:
    memory = FirebaseConversationMemory.__new__(FirebaseConversationMemory)
    memory.db = None
    memory._in_memory_fallback = {}
    return memory


def test_get_history_empty_conversation_returns_empty_list():
    memory = make_fallback_memory()
    assert memory.get_history("nonexistent") == []


def test_add_message_then_get_history_round_trips():
    memory = make_fallback_memory()
    memory.add_message("conv1", "What is hymn 2?", "The Spirit of God", user_id="user1")

    assert memory.get_history("conv1") == [("What is hymn 2?", "The Spirit of God")]


def test_conversations_are_isolated_from_each_other():
    memory = make_fallback_memory()
    memory.add_message("conv1", "q in conv1", "a in conv1", user_id="user1")
    memory.add_message("conv2", "q in conv2", "a in conv2", user_id="user1")

    assert memory.get_history("conv1") == [("q in conv1", "a in conv1")]
    assert memory.get_history("conv2") == [("q in conv2", "a in conv2")]


def test_history_is_trimmed_to_max_conversation_history():
    memory = make_fallback_memory()
    for i in range(MAX_CONVERSATION_HISTORY + 5):
        memory.add_message("conv1", f"q{i}", f"a{i}", user_id="user1")

    history = memory.get_history("conv1")

    assert len(history) == MAX_CONVERSATION_HISTORY
    assert history[0] == ("q5", "a5")
    assert history[-1] == (f"q{MAX_CONVERSATION_HISTORY + 4}", f"a{MAX_CONVERSATION_HISTORY + 4}")


def test_get_user_conversations_always_empty_without_firestore():
    memory = make_fallback_memory()
    memory.add_message("conv1", "hello", "hi", user_id="user1")

    # Documented limitation: the in-memory fallback has no per-user index
    # (it's keyed only by conversation_id), so this returns [] even though
    # conv1 exists and belongs to user1.
    assert memory.get_user_conversations("user1") == []
