import re
import sqlite3
import boto3
from boto3.dynamodb.conditions import Key
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
        columns = ["id", "role", "content", "conversation", "conversation_position"]
        df = pd.DataFrame(data, columns=columns)
        return df

    def delete_message(self, message_id):
        query = """
            DELETE FROM messages
            WHERE id = ?
        """
        self._query_db(query, (message_id,))

    def get_message(self, message_id):
        query = """
            SELECT id, role, content, conversation, conversation_position
            FROM messages
            WHERE id = ?
        """
        result = self._query_db(query, (message_id,), fetch="one")
        if result:
            message = {
                "id": result[0],
                "role": result[1],
                "content": result[2],
                "conversation": result[3],
                "conversation_position": result[4],
            }
            return message
        else:
            return None

    def list_conversations(self):
        query = """
            SELECT * FROM conversations
            ORDER BY last_updated DESC
        """
        data = self._query_db(query, fetch="all")
        columns = ["id", "title", "tags", "last_updated"]
        df = pd.DataFrame(data, columns=columns)
        return df

    def update_message(self, message_id, regex, substitution):
        message = self.get_message(message_id)
        if message:
            updated_content = re.sub(regex, substitution, message["content"])
            query = """
                UPDATE messages
                SET content = ?
                WHERE id = ?
            """
            self._query_db(query, (updated_content, message_id))
        else:
            print("Message not found.")

    def _create_tables(self):
        self._query_db(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                conversation INTEGER,
                conversation_position INTEGER
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
                WHERE conversation = {conversation_id}
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

    def _put_message(self, message, conversation_id, conversation_position):
        self._query_db(
            """
            INSERT INTO messages (role, content, conversation, conversation_position)
            VALUES (?, ?, ?, ?)
        """,
            (
                message["role"],
                message["content"],
                conversation_id,
                conversation_position,
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


class DynamoDatabase:
    def __init__(self) -> None:
        self.dynamodb = boto3.resource("dynamodb")
        self.messages_table = self.dynamodb.Table("messages")
        self.conversations_table = self.dynamodb.Table("conversations")

        self._create_tables()

    def _create_tables(self):
        # Create tables in DynamoDB (if not already created)
        pass

    def _get_context(self, conversation_id):
        response = self.messages_table.query(
            KeyConditionExpression=Key("conversation").eq(conversation_id),
            ScanIndexForward=True,
        )
        return [
            {"role": item["role"], "content": item["content"]}
            for item in response["Items"]
        ]

    def _get_max_conversation_id(self):
        max_id_resp = self.conversations_table.scan(
            Select="SPECIFIC_ATTRIBUTES",
            ProjectionExpression="id",
        )
        return max([item["id"] for item in max_id_resp["Items"]], default=0)

    def _put_conversation(self, conversation_id):
        self.conversations_table.put_item(
            Item={"id": conversation_id, "last_updated": str(self._get_utc_now())}
        )

    def _put_message(self, message, conversation_id, conversation_position):
        self.messages_table.put_item(
            Item={
                "id": f"{conversation_id}-{conversation_position}",
                "role": message["role"],
                "content": message["content"],
                "conversation": conversation_id,
                "conversation_position": conversation_position,
            }
        )

    def _update_conversation(self, conversation_id):
        self.conversations_table.update_item(
            Key={"id": conversation_id},
            UpdateExpression="SET last_updated = :last_updated",
            ExpressionAttributeValues={":last_updated": str(self._get_utc_now())},
        )

    def _get_utc_now(self):
        from datetime import datetime

        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
