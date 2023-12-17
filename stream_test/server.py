from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

# OpenAIクライアントのインスタンス化
client = OpenAI()


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):
    def generate():
        try:
            openai_stream = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": request.message}],
                stream=True,
            )
            for message in openai_stream:
                if message.choices[0].delta.content:
                    print(message.choices[0].delta.content)
                    yield message.choices[0].delta.content
                if message.choices[0].finish_reason == "stop":
                    break
        except Exception as e:
            yield f"Error: {str(e)}\n"

    return StreamingResponse(generate(), media_type="text/plain")
