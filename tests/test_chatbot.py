import pytest
import pandas as pd
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
    assert conversations.shape == (1, 4)


@pytest.mark.focus
def test_truncate_context():
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


def test_delete_conversation(chatbot):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        conversation_id = chatbot.upload_conversation(
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "Can you tell me a joke?"},
                {
                    "role": "assistant",
                    "content": "Sure, why did the chicken cross the road?",
                },
                {"role": "user", "content": "I don't know, why?"},
                {"role": "assistant", "content": "To get to the other side!"},
            ]
        )

    assert conversation_id in chatbot.list_conversations()["id"].tolist()

    chatbot.delete_conversation(conversation_id)

    assert conversation_id not in chatbot.list_conversations()["id"].tolist()

    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        conversation_id_1 = chatbot.upload_conversation(
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "Can you tell me a joke?"},
                {
                    "role": "assistant",
                    "content": "Sure, why did the chicken cross the road?",
                },
                {"role": "user", "content": "I don't know, why?"},
                {"role": "assistant", "content": "To get to the other side!"},
            ]
        )
        conversation_id_2 = chatbot.upload_conversation(
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "Can you tell me a joke?"},
                {
                    "role": "assistant",
                    "content": "Sure, why did the chicken cross the road?",
                },
                {"role": "user", "content": "I don't know, why?"},
                {"role": "assistant", "content": "To get to the other side!"},
            ]
        )

    assert conversation_id_1 in chatbot.list_conversations()["id"].tolist()
    assert conversation_id_2 in chatbot.list_conversations()["id"].tolist()

    chatbot.delete_conversation([conversation_id_1, conversation_id_2])

    assert conversation_id_1 not in chatbot.list_conversations()["id"].tolist()
    assert conversation_id_2 not in chatbot.list_conversations()["id"].tolist()


def test_get_messages(chatbot):
    with mock.patch.object(
        openai.ChatCompletion, "create", return_value=mock_openai_response()
    ):
        conversation_id = chatbot.upload_conversation(
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "Can you tell me a joke?"},
                {
                    "role": "assistant",
                    "content": "Sure, why did the chicken cross the road?",
                },
                {"role": "user", "content": "I don't know, why?"},
                {"role": "assistant", "content": "To get to the other side!"},
            ]
        )

    messages_df = chatbot.get_messages()

    expected_df = pd.DataFrame(
        [
            {
                "id": 1,
                "role": "user",
                "content": "Hello",
                "conversation_id": conversation_id,
                "conversation_position": 0,
                "token_count": 1,
            },
            {
                "id": 2,
                "role": "assistant",
                "content": "Hi there! How can I help you?",
                "conversation_id": conversation_id,
                "conversation_position": 1,
                "token_count": 9,
            },
            {
                "id": 3,
                "role": "user",
                "content": "Can you tell me a joke?",
                "conversation_id": conversation_id,
                "conversation_position": 2,
                "token_count": 7,
            },
            {
                "id": 4,
                "role": "assistant",
                "content": "Sure, why did the chicken cross the road?",
                "conversation_id": conversation_id,
                "conversation_position": 3,
                "token_count": 10,
            },
            {
                "id": 5,
                "role": "user",
                "content": "I don't know, why?",
                "conversation_id": conversation_id,
                "conversation_position": 4,
                "token_count": 7,
            },
            {
                "id": 6,
                "role": "assistant",
                "content": "To get to the other side!",
                "conversation_id": conversation_id,
                "conversation_position": 5,
                "token_count": 7,
            },
        ]
    )
    pd.testing.assert_frame_equal(messages_df, expected_df)
