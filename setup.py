from setuptools import setup

setup(
    name='chatgpt',
    version='0.1.0',
    description='A package for GPT based chatbot',
    author='Joshua Cook',
    author_email='root@joshuacook.net',
    url='https://github.com/joshuacook/chatgpt',
    packages=['chatgpt'],
    install_requires=[
        "boto3",
        "jupyterlab",
        "openai",
        "gradio",
        "tiktoken"
    ]
)