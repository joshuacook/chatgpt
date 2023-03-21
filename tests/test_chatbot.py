import pytest
import os
from chatgpt.chatbot import Chatbot
import unittest.mock as mock
import openai


def mock_openai_response():
    return [
        {
            "choices": [
                {
                    "delta": {
                        "role": "assistant",
                        "content": "This is a mocked response.",
                    }
                }
            ]
        }
    ]


@pytest.fixture
def chatbot():
    chatbot_instance = Chatbot(db_path="test.db")

    yield chatbot_instance

    os.remove("test.db")


def test_chatbot_init(chatbot):
    assert chatbot.conversation_id is not None
    assert chatbot.engine == "gpt-3.5-turbo"
    assert chatbot.temperature == 0.8
    assert chatbot.max_tokens == 3200

    new_chatbot = Chatbot(conversation_id=1, db_path="test.db")
    assert new_chatbot.conversation_id == 1

    new_chatbot = Chatbot(conversation_id=2, db_path="test.db")
    assert new_chatbot.conversation_id == 2


def test_talk_to_me(chatbot):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        chatbot.talk_to_me("Hello")
        context = chatbot.database._get_context(chatbot.conversation_id)

        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "Hello"
        assert context[1]["role"] == "assistant"
        assert context[1]["content"] == "This is a mocked response."


def test_delete_message(chatbot):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        chatbot.talk_to_me("First message")
        chatbot.talk_to_me("Second message")

        context = chatbot.database._get_context(chatbot.conversation_id)
        assert len(context) == 4

        chatbot.delete_message(3)  # Delete the second response from the assistant
        context = chatbot.database._get_context(chatbot.conversation_id)
        assert len(context) == 3


def test_find_message(chatbot):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        chatbot.talk_to_me("Find this unique message")
        chatbot.talk_to_me("Another message")

        found_messages = chatbot.find_message("unique message")
        assert len(found_messages) == 1
        assert found_messages.iloc[0]["content"] == "Find this unique message"


def test_list_conversations():
    chatbot1 = Chatbot(db_path="test.db", conversation_id=None)
    chatbot2 = Chatbot(db_path="test.db", conversation_id=None)  # noqa: F841
    chatbot3 = Chatbot(db_path="test.db", conversation_id=None)  # noqa: F841

    conversations = chatbot1.list_conversations()
    assert conversations.shape == (3, 4)


def test_truncate_context(chatbot):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        # Add messages to the conversation
        chatbot4 = Chatbot(db_path="test.db", max_tokens=20)
        for i in range(10):
            chatbot4.talk_to_me(f"Message {i}")

        context = chatbot4.database._get_context(chatbot4.conversation_id)
        assert len(context) == 20

        truncated_context = chatbot4._truncate_context(context)
        assert len(truncated_context) < 20

        summary_message = truncated_context[0]
        assert summary_message["role"] == "assistant"
