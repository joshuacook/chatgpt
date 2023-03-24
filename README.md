1. `conda create -n chatgpt python=3.10`
2. `conda activate chatgpt`
3. `pip install -r requirements.txt`
4. `jupyter lab`


```
from chatbot import Chatbot
cli = Chatbot()
cli.talk_to_me(my_prompt)
cli.print_context()
```

## To Install Jupyter Magic

```
ipython profile create default
vi ~/.ipython/profile_default/startup/chat_magic_startup.py
```

Add this to the new file:

```
from chatgpt.chatbot_magic import load_ipython_extension
from chatgpt.chatbot import Chatbot
from IPython import get_ipython

load_ipython_extension(get_ipython())
chatbot = Chatbot(database='local')
```

Restart the Jupyter Kernel, then run `%gpt help`.