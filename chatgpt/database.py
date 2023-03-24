import sqlite3
import pandas as pd


class LocalDatabase:
    def __init__(self, db_file="chat.db"):
        self.db_file = db_file

    def find_message(self, search_string):
        search_string = f"%{search_string}%"
        query = """
            SELECT * FROM messages
            WHERE content LIKE ?
        """
        data = self._query_db(query, (search_string,), fetch="all")
        columns = [
            "id",
            "role",
            "content",
            "conversation_id",
            "conversation_position",
            "token_count",
        ]
        df = pd.DataFrame(data, columns=columns)
        return df

    def delete_message(self, message_id):
        query = """
            DELETE FROM messages
            WHERE id = ?
        """
        self._query_db(query, (message_id,))

    def delete_conversation(self, conversation_id):
        query = """
            SELECT COUNT(*)
            FROM messages
            WHERE conversation_id = ?
        """
        message_count = self._query_db(query, (conversation_id,), fetch="one")[0]

        if message_count > 0:
            query = """
                DELETE FROM messages
                WHERE conversation_id = ?
            """
            self._query_db(query, (conversation_id,))

        query = """
            DELETE FROM conversations
            WHERE id = ?
        """
        self._query_db(query, (conversation_id,))

    def get_message(self, message_id):
        query = """
            SELECT
                id,
                role,
                content,
                conversation_id,
                conversation_position,
                token_count
            FROM messages
            WHERE id = ?
        """
        result = self._query_db(query, (message_id,), fetch="one")
        if result:
            message = {
                "id": result[0],
                "role": result[1],
                "content": result[2],
                "conversation_id": result[3],
                "conversation_position": result[4],
                "token_count": result[5],
            }
            return message
        else:
            return None

    def get_messages(self, predicate_sql=None):
        """
        Get all messages with their attributes as a pandas DataFrame.

        :param predicate_sql: An optional SQL WHERE clause to filter the results.
        :return: A pandas DataFrame containing message attributes.
        """
        query = "SELECT * FROM messages"

        if predicate_sql is not None:
            query += f" WHERE {predicate_sql}"

        result = self._query_db(query, fetch="all")

        messages_df = pd.DataFrame(
            result,
            columns=[
                "id",
                "role",
                "content",
                "conversation_id",
                "conversation_position",
                "token_count",
            ],
        )

        return messages_df

    def list_conversations(self):
        query = """
            SELECT * FROM conversations
            ORDER BY last_updated DESC
        """
        data = self._query_db(query, fetch="all")
        columns = ["id", "title", "tags", "last_updated"]
        df = pd.DataFrame(data, columns=columns)
        return df

    def _create_tables(self):
        self._query_db(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                conversation_id INTEGER,
                conversation_position INTEGER,
                token_count INTEGER
            )
        """
        )
        self._query_db(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                tags TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def _get_context(self, conversation_id):
        context = self._query_db(
            f"""
                SELECT role, content
                FROM messages
                WHERE conversation_id = {conversation_id}
                ORDER BY conversation_position
            """,
            fetch="all",
        )
        return [{"role": role, "content": content} for role, content in context]

    def _get_conversation_attributes(self, conversation_id):
        query = """
            SELECT id, title, tags, last_updated
            FROM conversations
            WHERE id = ?
        """
        result = self._query_db(query, (conversation_id,), fetch="one")
        if result:
            return {
                "id": result[0],
                "title": result[1],
                "tags": result[2],
                "last_updated": result[3],
            }
        return None

    def _get_max_conversation_id(self):
        result = self._query_db("SELECT MAX(id) FROM conversations", fetch="one")
        return result[0] if result[0] is not None else 0

    def _query_db(self, query, params=None, fetch=None):
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        if fetch == "all":
            data = cur.fetchall()
        elif fetch == "one":
            data = cur.fetchone()
        conn.commit()
        conn.close()
        if fetch in ("all", "one"):
            return data

    def _put_conversation(self, conversation_id):
        self._query_db(
            """
            INSERT INTO conversations (id)
            VALUES (?)
        """,
            (conversation_id,),
        )

    def _put_message(
        self, message, conversation_id, conversation_position, token_count
    ):
        self._query_db(
            """
            INSERT INTO messages (
                role,
                content,
                conversation_id,
                conversation_position,
                token_count
            )
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                message["role"],
                message["content"],
                conversation_id,
                conversation_position,
                token_count,
            ),
        )

    def _update_conversation(self, conversation_id):
        self._query_db(
            "UPDATE conversations SET last_updated = datetime('now') WHERE id = ?",
            (conversation_id,),
        )

    def update_conversation_title(self, conversation_id, title):
        query = """
            UPDATE conversations
            SET title = ?
            WHERE id = ?
        """
        self._query_db(query, (title, conversation_id))
