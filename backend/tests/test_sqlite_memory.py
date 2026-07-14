"""Unit tests for SQLiteConversationMemory against a temp DB file."""
import pytest

from sqlite_memory import SQLiteConversationMemory


@pytest.fixture
def memory(tmp_path):
    db_path = tmp_path / "conversations.db"
    return SQLiteConversationMemory(db_path=str(db_path))


def test_get_history_empty_conversation_returns_empty_list(memory):
    assert memory.get_history("nonexistent") == []


def test_add_message_then_get_history_round_trips(memory):
    memory.add_message("conv1", "What is hymn 2?", "The Spirit of God", user_id="user1")

    history = memory.get_history("conv1")

    assert history == [("What is hymn 2?", "The Spirit of God")]


def test_history_preserves_chronological_order(memory):
    memory.add_message("conv1", "first question", "first answer", user_id="user1")
    memory.add_message("conv1", "second question", "second answer", user_id="user1")
    memory.add_message("conv1", "third question", "third answer", user_id="user1")

    history = memory.get_history("conv1")

    assert history == [
        ("first question", "first answer"),
        ("second question", "second answer"),
        ("third question", "third answer"),
    ]


def test_conversations_are_isolated_from_each_other(memory):
    memory.add_message("conv1", "q in conv1", "a in conv1", user_id="user1")
    memory.add_message("conv2", "q in conv2", "a in conv2", user_id="user1")

    assert memory.get_history("conv1") == [("q in conv1", "a in conv1")]
    assert memory.get_history("conv2") == [("q in conv2", "a in conv2")]


def test_get_user_conversations_returns_only_that_users_conversations(memory):
    memory.add_message("conv1", "hello", "hi", user_id="user1")
    memory.add_message("conv2", "hello", "hi", user_id="user2")

    convs = memory.get_user_conversations("user1")

    assert len(convs) == 1
    assert convs[0]["id"] == "conv1"


def test_get_user_conversations_with_no_user_id_returns_empty(memory):
    assert memory.get_user_conversations("") == []
    assert memory.get_user_conversations(None) == []


def test_first_message_sets_conversation_title_from_query(memory):
    long_query = "a" * 100
    memory.add_message("conv1", long_query, "answer", user_id="user1")

    convs = memory.get_user_conversations("user1")

    assert convs[0]["title"] == long_query[:50]


def test_title_does_not_change_on_subsequent_messages(memory):
    memory.add_message("conv1", "first title", "answer", user_id="user1")
    memory.add_message("conv1", "second message should not overwrite title", "answer2", user_id="user1")

    convs = memory.get_user_conversations("user1")

    assert convs[0]["title"] == "first title"
