from fastapi import FastAPI, Request, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from openai import OpenAI
from openai import AssistantEventHandler
import threading
import queue
import asyncio
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import json

# OpenAIクライアントのインスタンス化
client = OpenAI()


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
            model="gpt-4o",
        )
        # app.state.my_thread = client.beta.threads.create()
        print("-----assistantの生成-------")
        print(app.state.assistant)
        # print("------threadの生成---------")
        # print(app.state.my_thread)

        yield  # サーバが起動している間、ここで待機

    finally:
        # アプリケーションのクリーンアップ
        print("アプリケーションが終了します。")
        # ここでデータベースの接続解除やクリーンアップを行う
        # スレッドとアシスタントを削除するクリーンアップ処理を行います。
        # if app.state.my_thread:
        #     result_del = client.beta.threads.delete(app.state.my_thread.id)
        #     print(result_del)

        if app.state.assistant:
            result_del_assistant = client.beta.assistants.delete(app.state.assistant.id)
            print(result_del_assistant)


app = FastAPI(lifespan=app_lifespan)  # type: ignore

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可する場合
    allow_credentials=True,
    allow_methods=["*"],  # すべてのメソッドを許可する場合
    allow_headers=["*"],  # すべてのヘッダーを許可する場合
)


# リクエストクラス
class ChatRequest(BaseModel):
    message: str = Field(..., description="メッセージ内容")
    thread_id: Optional[str] = Field(None, description="現在の会話のthread_id")


@app.post("/chat")
async def chat(request: ChatRequest):
    thread_id = request.thread_id
    if not request.thread_id:
        # 初回アクセスは新しいThreadを作成
        thread = client.beta.threads.create()
        thread_id = thread.id

    # ユーザーのメッセージをスレッドに追加
    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=request.message  # type: ignore
    )

    # メッセージとスレッドIDを返す
    res_dict = {"thread_id": thread_id, "message": "message received..."}
    return res_dict


def stream_data(q):
    """イベントストリーム形式でデータを生成するジェネレータ"""
    try:
        while True:
            data = q.get()
            print(data, end="", flush=True)
            if data == "STOP":
                break
            # JSONでエンコードしてからSSEフォーマットで送信
            yield f'data: {json.dumps({"message": data})}\n\n'
            q.task_done()
    finally:
        q.task_done()


@app.get("/stream/{thread_id}")
async def stream_response(
    base: Request, thread_id: str = Path(..., description="threadのid")
):
    assistant = base.app.state.assistant
    q = queue.Queue()

    class EventHandler(AssistantEventHandler):
        def on_text_created(self, text):
            # q.put(f"\n")
            q.put("")

        def on_text_delta(self, delta, snapshot):
            q.put(delta.value)

        def on_tool_call_created(self, tool_call):
            # q.put(f"\n{tool_call.type}\n")
            q.put(f"{tool_call.type}")

        def on_tool_call_delta(self, delta, snapshot):
            if delta.type == "code_interpreter":
                if delta.code_interpreter.input:  # type: ignore
                    q.put(delta.code_interpreter.input)  # type: ignore
                if delta.code_interpreter.outputs:  # type: ignore
                    q.put(f"\n\noutput >")
                    for output in delta.code_interpreter.outputs:  # type: ignore
                        if output.type == "logs":
                            q.put(f"\n{output.logs}")

    def assistant_event():
        try:
            with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant.id,
                event_handler=EventHandler(),
            ) as stream:
                stream.until_done()
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            q.put("STOP")

    assistant_event_thread = threading.Thread(target=assistant_event)
    assistant_event_thread.start()

    # # 既存のThreadを使用してメッセージを取得
    # async def event_stream():
    #     while True:
    #         # OpenAIからの応答を待機し、発生するたびにyield
    #         # サンプルでは応答をシミュレート
    #         yield f'data: {{"message": "Response from OpenAI"}}\n\n'
    #         await asyncio.sleep(1)  # 応答間隔をシミュレート

    return StreamingResponse(stream_data(q), media_type="text/event-stream")
