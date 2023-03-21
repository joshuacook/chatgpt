import openai
import os
from .database import LocalDatabase, DynamoDatabase
from IPython.display import display, Markdown


class Chatbot:
    def __init__(
        self,
        conversation_id: int = None,
        database: str = "local",
        db_path: str = "chat.db",
        max_tokens: int = 3200,
    ):
        self.conversation_id = conversation_id
        self.engine = "gpt-3.5-turbo"
        self.temperature = 0.8
        self.max_tokens = max_tokens

        if database == "local":
            self.database = LocalDatabase(db_file=db_path)
        elif database == "dynamo":
            self.database = DynamoDatabase()
        self.database._create_tables()

        if conversation_id is None:
            max_id = self.database._get_max_conversation_id()
            self.conversation_id = max_id + 1
            self.database._put_conversation(self.conversation_id)
            self.title = None
        else:
            self.conversation_id = conversation_id
            conversation_attributes = self.database._get_conversation_attributes(
                conversation_id
            )
            if conversation_attributes is None:
                self.title = None
                self.database._put_conversation(self.conversation_id)
            else:
                self.title = conversation_attributes["title"]

        openai.api_key = os.getenv("OPENAI_API_KEY")

    def talk_to_me(self, prompt, context=None):
        if context is None:
            context = self.database._get_context(self.conversation_id)

        new_message = self._submit_prompt_for_streaming(prompt, context)

        self.database._put_message(context[-1], self.conversation_id, len(context) - 1)
        self.database._put_message(new_message, self.conversation_id, len(context))

        if self.title is None:
            self.update_conversation_title()
        self.database._update_conversation(self.conversation_id)

    def delete_message(self, message_id):
        self.database.delete_message(message_id)

    def find_message(self, search_string):
        return self.database.find_message(search_string)

    def list_conversations(self):
        return self.database.list_conversations()

    def update_message(self, message_id, match, substitution=""):
        self.database.update_message(message_id, match, substitution)

    def update_conversation_title(self):
        context = self.database._get_context(self.conversation_id)
        self.title = self._generate_title(context)
        self.database.update_conversation_title(self.conversation_id, self.title)

    def print_context(self, markdown=True):
        context = self.database._get_context(self.conversation_id)
        if len(context) > 0 and self.title is None:
            self.update_conversation_title()
        if markdown:
            output = f"# {self.title}\n\n"
        else:
            print(self.title, end="\n\n")
        for message in context:
            if markdown:
                output = ""
                output += f"**{message['role'].upper()}**:\n"
                output += message["content"].replace("\n", "  \n")
                output += "\n\n"
                display(Markdown(output))
            else:
                print(message["role"].upper(), message["content"], sep="\n", end="\n\n")

    def _generate_summary(self, context):
        new_message = self._submit_prompt_for_streaming(
            "Can you summarize this conversation:\n\n", context, display=False
        )
        return new_message["content"].replace("\n", " ")

    def _generate_title(self, context):
        print("\n\nGenerating title...\n")
        new_message = self._submit_prompt_for_streaming(
            "Can you generate a title for this conversation:\n\n", context
        )
        return new_message["content"].replace("\n", " ")

    def _stream_content(self, response, display):
        new_message = {"content": ""}
        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            if "role" in delta.keys():
                role = delta["role"]
                new_message["role"] = role
                if display:
                    print(role, end=" ")
            if "content" in delta.keys():
                content = delta["content"]
                new_message["content"] += content
                if display:
                    print(content, end="")
        return new_message

    def _submit_prompt_for_streaming(
        self,
        prompt,
        context,
        engine=None,
        temperature=None,
        max_tokens=None,
        n=1,
        display=True,
    ):
        if engine is None:
            engine = self.engine
        if temperature is None:
            temperature = self.temperature
        if max_tokens is None:
            max_tokens = self.max_tokens

        context.append({"role": "user", "content": prompt})
        response = openai.ChatCompletion.create(
            model=self.engine,
            messages=context,
            temperature=temperature,
            stream=True,
            max_tokens=max_tokens,
            n=1,
        )
        new_message = self._stream_content(response, display=display)
        return new_message

    def _truncate_context(self, context):
        truncated_context = []
        summary_context = []

        context_length = 0
        max_context_length = int(
            0.8 * (self.max_tokens - 100)
        )  # 80% of the available tokens

        for message in reversed(context):
            message_length = len(message["content"].split())

            if context_length + message_length <= max_context_length:
                truncated_context.append(message)
                context_length += message_length
            else:
                summary_context.append(message)

        if summary_context:
            summary_context = list(reversed(summary_context))
            summary = self._generate_summary(summary_context)
            truncated_context.insert(0, {"role": "assistant", "content": summary})

        return list(reversed(truncated_context))
