import openai
import os
from .database import LocalDatabase
from IPython.display import display, Markdown
import tiktoken

HOME = os.getenv("HOME")


class Chatbot:
    def __init__(
        self,
        conversation_id: int = None,
        database: str = "local",
        db_path: str = None,
        max_tokens: int = 3200,
        system=None,
    ):
        if db_path is None:
            self.db_path = f"{HOME}/.chatgpt/chat.db"
        else:
            self.db_path = db_path
        os.makedirs(f"{HOME}/.chatgpt", exist_ok=True)
        self.conversation_id = conversation_id
        self.engine = "gpt-3.5-turbo"
        self.temperature = 0.8
        self.max_tokens = max_tokens
        self.system = system

        if database == "local":
            self.database = LocalDatabase(db_file=self.db_path)
        self.database._create_tables()
        current_conversations = self.list_conversations()
        empty_conversations = current_conversations[
            current_conversations["title"].isnull()
        ]
        self.delete_conversation(empty_conversations["id"].tolist())

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
                self.title = conversation_attributes.get("title", None)

        openai.api_key = os.getenv("OPENAI_API_KEY")

    def talk_to_me(self, prompt, context=None):
        if context is None:
            context = self.database._get_context(self.conversation_id)
        if self.system is not None:
            context = [{"role": "system", "content": self.system}] + context
        new_message = self._submit_prompt(prompt, context)
        prompt_token_count = self._count_tokens(prompt)
        new_message_token_count = self._count_tokens(new_message["content"])
        self.database._put_message(
            context[-1], self.conversation_id, len(context) - 1, prompt_token_count
        )
        self.database._put_message(
            new_message, self.conversation_id, len(context), new_message_token_count
        )

        if self.title is None:
            self.update_conversation_title()
        self.database._update_conversation(self.conversation_id)

    def delete_message(self, message_id):
        self.database.delete_message(message_id)

    def delete_conversation(self, conversation_id):
        if type(conversation_id) is list:
            for id in conversation_id:
                self.database.delete_conversation(id)
        else:
            self.database.delete_conversation(conversation_id)

    def get_messages(self):
        return self.database.get_messages(f"conversation_id = {self.conversation_id}")

    def find_message(self, search_string):
        return self.database.find_message(search_string)

    def list_conversations(self):
        return self.database.list_conversations()

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

    def update_conversation_title(self, title=None):
        context = self.database._get_context(self.conversation_id)
        if title is None:
            self.title = self._generate_title(context[:1])
        else:
            self.title = title
        self.database.update_conversation_title(self.conversation_id, self.title)

    def upload_conversation(self, conversation_list):
        """
        Upload a conversation to the database.

        :param conversation_list:
            A list of dictionaries with schema {role: str, content: str}.
        """
        max_id = self.database._get_max_conversation_id()
        new_conversation_id = max_id + 1
        self.database._put_conversation(new_conversation_id)
        self.conversation_id = new_conversation_id

        for index, message in enumerate(conversation_list):
            role = message["role"]
            content = message["content"]

            if role not in ["user", "assistant"]:
                raise ValueError(
                    "Invalid role in the conversation list. "
                    "Must be 'user' or 'assistant'."
                )

            token_count = self._count_tokens(content)

            self.database._put_message(
                {"role": role, "content": content},
                new_conversation_id,
                index,
                token_count,
            )

        self.conversation_id = new_conversation_id
        self.update_conversation_title()
        self.database._update_conversation(self.conversation_id)

        return new_conversation_id

    def _count_tokens(self, text: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        try:
            tokens = list(encoding.encode(text))
            return len(tokens)
        except Exception as e:
            print(f"Error: {e}")
            return 0

    def _generate_summary(self, context):
        new_message = self._submit_prompt(
            "Can you summarize this conversation:\n\n", context, display=False
        )
        return new_message["content"].replace("\n", " ")

    def _generate_title(self, context):
        print("\n\nGenerating title...\n")
        new_message = self._submit_prompt(
            "Can you generate a title for this conversation:\n\n", context
        )
        return new_message["content"].replace("\n", " ")

    def _get_content(self, response, display):
        new_message = {"content": ""}
        for chunk in response:
            try:
                delta = chunk["choices"][0]["delta"]
            except TypeError:
                breakpoint()
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

    def _get_content_streamed(self, response):
        message = ""
        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta.keys():
                content = delta["content"]
                message += content
                if "\n" in content:
                    yield message
                    message = ""

    def _submit_prompt(
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
            stream=False,
            max_tokens=max_tokens,
            n=n,
        )
        content = self._get_content(response, display=display)
        return content

    def _submit_prompt_for_streaming(
        self,
        prompt,
        context,
        engine=None,
        temperature=None,
        max_tokens=None,
        n=1,
        display=True,
        **kwargs,
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
            n=n,
        )
        content = self._get_content_streamed(response)
        for new_message in content:
            yield new_message

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
