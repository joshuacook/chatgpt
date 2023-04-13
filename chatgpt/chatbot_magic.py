from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from chatgpt.chatbot import Chatbot
from IPython.display import display


@magics_class
class ChatbotMagics(Magics):
    def __init__(self, shell):
        super().__init__(shell)
        self.chatbot = Chatbot()

    @cell_magic
    def chat(self, line, cell):
        self.chatbot.talk_to_me(cell)

    @line_magic
    def gpt(self, line):
        _input = line.split(" ")
        if _input[0] == "help":
            print(
                """
                These commands are available via the %gpt magic:

                eg.

                %gpt help
                %gpt ls conversations

                help: print this message
                ls conversations: list conversations
                ls messages: list messages
                set conversation_id: set conversation id
                set max_tokens: set max tokens
                set system: set system
                set engine: set engine
                set temperature: set temperature
                show: show conversation
                rm conversation: remove conversation
                rm message: remove message
                attrs: print attributes

                To talk to the bot, use the %%chat magic:

                %%chat

                What is the capital of France?
                """
            )
        elif _input[0] == "show":
            self.chatbot.print_context()
        elif _input[0] == "ls":
            if _input[1] == "conversations":
                display(self.chatbot.list_conversations())
            elif _input[1] == "messages":
                display(self.chatbot.get_messages())
        elif _input[0] == "set":
            param, value = _input[1], _input[2]
            if param in ("max_tokens", "conversation_id"):
                value = int(value)
            if param == "system":
                value = " ".join(_input[2:])
            setattr(self.chatbot, param, value)
        elif _input[0] == "rm":
            if _input[1] == "conversation":
                self.chatbot.delete_conversation(int(_input[2]))
            elif _input[1] == "message":
                self.chatbot.delete_message(int(_input[2]))
        elif _input[0] == "attrs":
            print("conversation_id", self.chatbot.conversation_id, sep=": ")
            print("max_tokens", self.chatbot.max_tokens, sep=": ")
            print("system", self.chatbot.system, sep=": ")
            print("engine", self.chatbot.engine, sep=": ")
            print("temperature", self.chatbot.temperature, sep=": ")


# Function to load the extension in IPython
def load_ipython_extension(ipython):
    ipython.register_magics(ChatbotMagics)
