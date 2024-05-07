#!/usr/bin/env python3
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI
import os
import traceback
import contextlib
from dotenv import load_dotenv
from common.utils import update_env_file
from common.helper import StreamingEventHandler

# 環境変数をロードし、OpenAIクライアントを初期化します。
load_dotenv(override=True)
client = OpenAI()
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_ID = os.getenv("THREAD_ID")


# class EventHandler(AssistantEventHandler):
#     @override
#     def on_text_created(self, text) -> None:
#         print(f"\nassistant > ", end="", flush=True)

#     @override
#     def on_tool_call_created(self, tool_call):
#         print(f"\nassistant > {tool_call.type}\n", flush=True)

#     @override
#     def on_message_done(self, message) -> None:
#         # print a citation to the file searched
#         message_content = message.content[0].text
#         annotations = message_content.annotations
#         citations = []
#         for index, annotation in enumerate(annotations):
#             message_content.value = message_content.value.replace(
#                 annotation.text, f"[{index}]"
#             )
#             if file_citation := getattr(annotation, "file_citation", None):
#                 cited_file = client.files.retrieve(file_citation.file_id)
#                 citations.append(f"[{index}] {cited_file.filename}")

#         print(message_content.value)
#         print("\n".join(citations))


def response_chatbot(assistant, thread, user_input):
    message = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_input
    )

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        # instructions="Please address the user as Jane Doe. The user has a premium account.",
        event_handler=StreamingEventHandler(assistant_pronpt="チャットボット: "),
    ) as stream:
        stream.until_done()


def main():
    """
    メイン関数。環境変数からアシスタントとスレッドのIDを取得し、
    チャットボットのセッションを開始します。ユーザーの入力に応じて応答を生成し、
    特定のキーワードでセッションを終了します。
    """
    try:

        # アシスタントのインスタンスを取得または作成します。
        assistant = (
            client.beta.assistants.retrieve(ASSISTANT_ID)
            if ASSISTANT_ID
            else client.beta.assistants.create(
                instructions="あなたはカスタマーサポートのチャットボットです。ナレッジベースを活用して、顧客からの問い合わせに最適な対応をしましょう。ユーザーには日本語で回答してください。",
                model="gpt-4-turbo",
                tools=[{"type": "file_search"}],
            )
        )

        # vector storeを作成する
        vector_store = client.beta.vector_stores.create(name="Sample_manual")

        # OpenAIにアップロードするファイルを準備する
        # contextLib.ExitStackは、登録されたすべてのコンテキストマネージャ（この場合はファイルオブジェクト）を適切に閉じることを保証します。
        with contextlib.ExitStack() as stack:
            # ファイルをアシスタントにアップロードします。
            file = client.files.create(
                file=stack.enter_context(open("./sample_files/manual.pdf", "rb")),
                purpose="assistants",
            )

            file_batch = client.beta.vector_stores.file_batches.create_and_poll(
                vector_store_id=vector_store.id, file_ids=[file.id]
            )

            print(file_batch.status)
            print(file_batch.file_counts)

        # アシスタントにvector storeを参照させるようにアップデートする
        assistant = client.beta.assistants.update(
            assistant_id=assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )

        # スレッドのインスタンスを取得または作成します。
        thread = (
            client.beta.threads.retrieve(THREAD_ID)
            if THREAD_ID
            else client.beta.threads.create()
        )

        # 環境変数ファイルを更新します。
        update_env_file(".env", "ASSISTANT_ID", assistant.id)
        update_env_file(".env", "THREAD_ID", thread.id)

        # インスタンスの削除フラグを設定します。
        delete_instance = False

        # チャットボットの開始メッセージを表示します。
        print("チャットボット: こんにちは！何か聞きたいことはありますか？")
        while True:
            # ユーザーからの入力を受け取ります。
            user_input = input("あなた: ")

            # 特定のキーワードでチャットを終了します。
            if user_input.lower() == "またね":
                print("チャットボット: また会いましょう！")
                break

            # 特定のキーワードで、インスタンスを削除して終了します。
            if user_input.lower() == "さようなら":
                delete_instance = True
                print("チャットボット: assistantとthreadを削除します。さようなら。")
                break

            # チャットボットの応答を得ます。
            res = response_chatbot(assistant, thread, user_input)
            # for response_text in res:
            #     print(response_text)

    except Exception as e:
        # 予期せぬエラーが発生した場合のエラーメッセージを出力します。
        print("予期せぬエラーが発生しました:", e)
        print(traceback.print_exc())
    finally:
        # セッション終了時にインスタンスを削除するためのクリーンアップ処理を行います。
        if delete_instance:
            if assistant:
                result_del_assistant = client.beta.assistants.delete(assistant.id)
                print(result_del_assistant)
            if file:
                result_del_file = client.files.delete(file_id=file.id)
                print(result_del_file)
            if thread:
                result_del_thread = client.beta.threads.delete(thread.id)
                print(result_del_thread)

            # 環境変数ファイルをクリアします。
            update_env_file(".env", "ASSISTANT_ID", "")
            update_env_file(".env", "THREAD_ID", "")


# メイン関数を実行します。
if __name__ == "__main__":
    main()
