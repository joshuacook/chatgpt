import pytest
import os
from chatgpt.database import LocalDatabase


@pytest.fixture
def test_db():
    db = LocalDatabase(db_file="test.db")
    db._create_tables()
    yield db

    os.remove("test.db")


def test_get_message(test_db):
    # Insert a sample message
    test_db._put_message({"role": "user", "content": "Sample message"}, 1, 1, 1)

    # Test get_message method
    message = test_db.get_message(1)
    assert message is not None
    assert message["id"] == 1
    assert message["role"] == "user"
    assert message["content"] == "Sample message"
    assert message["conversation_id"] == 1
    assert message["conversation_position"] == 1
    assert message["token_count"] == 1
