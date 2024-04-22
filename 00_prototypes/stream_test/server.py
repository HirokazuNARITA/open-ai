from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from openai import AssistantEventHandler
import threading
import queue
from contextlib import asynccontextmanager


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    try:
        # アプリケーションの初期化
        print("アプリケーションが開始します。")
        # ここでデータベース接続や初期設定を行う
        app.state.assistant = client.beta.assistants.create(
            name="数学の家庭教師",
            description="あなたは数学の家庭教師です。コードを書いて実行し、数学の質問に答えてください。",
            tools=[{"type": "code_interpreter"}],
            model="gpt-4-turbo-2024-04-09",
        )
        app.state.my_thread = client.beta.threads.create()
        print("-----assistantの生成-------")
        print(app.state.assistant)
        print("------threadの生成---------")
        print(app.state.my_thread)

        yield  # サーバが起動している間、ここで待機

    finally:
        # アプリケーションのクリーンアップ
        print("アプリケーションが終了します。")
        # ここでデータベースの接続解除やクリーンアップを行う
        # スレッドとアシスタントを削除するクリーンアップ処理を行います。
        if app.state.my_thread:
            result_del = client.beta.threads.delete(app.state.my_thread.id)
            print(result_del)

        if app.state.assistant:
            result_del_assistant = client.beta.assistants.delete(app.state.assistant.id)
            print(result_del_assistant)


app = FastAPI(lifespan=app_lifespan)

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


# パターンA
@app.post("/assistant")
def assistant_stream(request: ChatRequest, base: Request):
    my_thread = base.app.state.my_thread
    assistant = base.app.state.assistant

    def generate():
        try:
            client.beta.threads.messages.create(
                thread_id=my_thread.id, role="user", content=request.message
            )

            with client.beta.threads.runs.stream(
                thread_id=my_thread.id, assistant_id=assistant.id
            ) as stream:
                for text in stream.text_deltas:
                    yield text

        except Exception as e:
            yield f"Error: {str(e)}\n"

    return StreamingResponse(generate(), media_type="text/plain")


# パターンB
# イベントを格納するキュー
event_queue = queue.Queue()


def stream_data(q):
    """ストリーミング用のジェネレータ関数"""
    try:
        while True:
            data = q.get()
            print(data, end="", flush=True)
            if data == "STOP":
                break
            yield data
            # time.sleep(1)  # デモのための遅延
    finally:
        print("Closing stream...")
        q.task_done()


@app.post("/assistant/queue")
async def assistant_queue(request: ChatRequest, base: Request):
    my_thread = base.app.state.my_thread
    assistant = base.app.state.assistant
    q = queue.Queue()

    # ストリーミング用のジェネレータを起動
    generator = stream_data(q)

    class EventHandler(AssistantEventHandler):
        def on_text_created(self, text):
            q.put(f"\nassistant > ")

        def on_text_delta(self, delta, snapshot):
            q.put(delta.value)

        def on_tool_call_created(self, tool_call):
            q.put(f"\nassistant > {tool_call.type}\n")

        def on_tool_call_delta(self, delta, snapshot):
            if delta.type == "code_interpreter":
                if delta.code_interpreter.input:
                    q.put(delta.code_interpreter.input)
                if delta.code_interpreter.outputs:
                    q.put(f"\n\noutput >")
                    for output in delta.code_interpreter.outputs:
                        if output.type == "logs":
                            q.put(f"\n{output.logs}")

    client.beta.threads.messages.create(
        thread_id=my_thread.id, role="user", content=request.message
    )

    def assistant_event():
        try:
            with client.beta.threads.runs.stream(
                thread_id=my_thread.id,
                assistant_id=assistant.id,
                # instructions="Please address the user as Jane Doe. The user has a premium account.",
                event_handler=EventHandler(),
            ) as stream:
                stream.until_done()

        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            print("Stopping the data addition thread.")
            q.put("STOP")

    assistant_event_thread = threading.Thread(target=assistant_event)
    assistant_event_thread.start()

    return StreamingResponse(generator, media_type="text/plain")
