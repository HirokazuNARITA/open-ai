#!/usr/bin/env python3
from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv
from common.utils import update_env_file
from common.helper import transform_latest_assistant_messages, retrieve_runs


client = OpenAI()
load_dotenv()
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_ID = os.getenv("THREAD_ID")


def response_chatbot(assistant, thread, user_input):
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_input
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="ユーザーには日本語で回答してください。",
    )
    run = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id, max_time=360)
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_msg_list = transform_latest_assistant_messages(messages=messages)

    result = []
    for data in assistant_msg_list:
        result.append(f"チャットボット: {data['content']['value']}")
    return result


def main():
    try:
        file = None
        # file = client.files.create(
        #     file=open("./sample_files/manual.pdf", "rb"), purpose="assistants"
        # )

        assistant = (
            client.beta.assistants.retrieve(ASSISTANT_ID)
            if ASSISTANT_ID
            else client.beta.assistants.create(
                instructions="あなたはカスタマーサポートのチャットボットです。ナレッジベースを活用して、顧客からの問い合わせに最適な対応をしましょう。",
                model="gpt-4-1106-preview",
                tools=[{"type": "retrieval"}],
                # file_ids=[file.id],
            )
        )

        thread = (
            client.beta.threads.retrieve(THREAD_ID)
            if THREAD_ID
            else client.beta.threads.create()
        )

        update_env_file(".env", "ASSISTANT_ID", assistant.id)
        update_env_file(".env", "THREAD_ID", thread.id)

        # インスタンスの削除フラグ
        delete_instance = False

        print("チャットボット: こんにちは！何か聞きたいことはありますか？")
        while True:
            # ユーザーからの入力を受け取る
            user_input = input("あなた: ")

            # 特定のキーワードでチャットを終了する
            if user_input.lower() == "またね":
                print("チャットボット: また会いましょう！")
                break

            # 特定のキーワードで、インスタンスを削除して終了する
            if user_input.lower() == "さようなら":
                delete_instance = True
                print("チャットボット: assistantとthreadを削除します。さようなら。")
                break

            # チャットボットの応答を得る
            res = response_chatbot(assistant, thread, user_input)
            for response_text in res:
                print(response_text)

    except Exception as e:
        print("予期せぬエラーが発生しました:", e)
        print(traceback.print_exc())
    finally:
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

            update_env_file(".env", "ASSISTANT_ID", "")
            update_env_file(".env", "THREAD_ID", "")


if __name__ == "__main__":
    main()
