from chatgpt.chatbot_magic import load_ipython_extension
from chatgpt.chatbot import Chatbot
from IPython import get_ipython

load_ipython_extension(get_ipython())
chatbot = Chatbot(database="local")
