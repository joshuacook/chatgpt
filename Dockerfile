FROM jupyter/scipy-notebook
RUN git clone https://github.com/joshuacook/chatgpt.git
WORKDIR chatgpt
RUN pip install -e .
RUN ipython profile create default
RUN cp bin/chat_magic_startup.py ~/.ipython/profile_default/startup/chat_magic_startup.py
