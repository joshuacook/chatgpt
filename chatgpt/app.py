from flask import Flask, Response, render_template, request
import json
from .chatbot import Chatbot

app = Flask(__name__)

chatbot = Chatbot()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    print(request.json)
    prompt = request.json["prompt"]
    context = chatbot.database._get_context(chatbot.conversation_id)

    def generate_response():
        for new_message in chatbot._submit_prompt_for_streaming(
            prompt, context, display=False
        ):
            yield json.dumps({"response": new_message})

    return Response(
        generate_response(),
        mimetype="text/json",
        headers={"Transfer-Encoding": "chunked"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
