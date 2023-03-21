import openai
import sqlite3
import os

class Chatbot:
    def __init__(self, conversation_id: int = None):
        self.db_file = "chat.db"
        self.conversation_id = conversation_id
        self.engine = "gpt-3.5-turbo"
        self.temperature = 0.8
        self._create_tables()

        if conversation_id is None:
            query = "SELECT MAX(id) FROM conversations"
            result = self._query_db(query, fetch="one")
            max_id = result[0]

            if max_id is None:
                self.conversation_id = 1
            else:
                self.conversation_id = max_id + 1

            # Create a new conversation record in the database
            self._query_db("""
                INSERT INTO conversations (id)
                VALUES (?)
            """, (self.conversation_id,))

        else:
            self.conversation_id = conversation_id

        openai.api_key = os.getenv("OPENAI_API_KEY")

    
    def talk_to_me(self, prompt, context=None):
        if context is None:
            context = self._query_db(
                f"SELECT role, content FROM messages WHERE conversation = {self.conversation_id} ORDER BY conversation_position",
                fetch="all"
            )
            context = [{"role": role, "content": content} for role, content in context]

        context.append({
            "role": "user",
            "content": prompt
        })
        response = openai.ChatCompletion.create(
            model=self.engine,
            messages=context,
            temperature=self.temperature,
            stream=True,
            max_tokens=3200,
            n=1,
        )
        new_message = {"content": ""}

        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            if "role" in delta.keys():
                new_message["role"] = delta["role"]
                print(delta["role"], end=" ")
            if "content" in delta.keys():
                new_message["content"] += delta["content"]
                print(delta["content"], end="")

        self._query_db("""
            INSERT INTO messages (role, content, conversation, conversation_position)
            VALUES (?, ?, ?, ?)
        """, (context[-1]["role"], context[-1]["content"], self.conversation_id, len(context)-1))

        self._query_db("""
            INSERT INTO messages (role, content, conversation, conversation_position)
            VALUES (?, ?, ?, ?)
        """, (new_message["role"], new_message["content"], self.conversation_id, len(context)))

        self._query_db("UPDATE conversations SET last_updated = datetime('now') WHERE id = ?", (self.conversation_id,))
 

    def _create_tables(self):
        self._query_db('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                conversation INTEGER,
                conversation_position INTEGER
            )
        ''')
        self._query_db('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
    def _get_context(self):
        context = self._query_db(
            f"""
                SELECT role, content
                FROM messages
                WHERE conversation = {self.conversation_id}
                ORDER BY conversation_position
            """,
            fetch="all"
        )
        return [{"role": role, "content": content} for role, content in context]
    
    def print_context(self):
        for message in self._get_context():
            print(message["role"].upper(), message["content"], sep="\n", end="\n\n")
        
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


