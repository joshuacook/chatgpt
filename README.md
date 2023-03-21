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