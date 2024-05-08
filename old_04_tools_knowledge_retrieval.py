#!/usr/bin/env python3
from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv
from dotenv import load_dotenv
from common.utils import update_env_file
from common.helper import transform_latest_assistant_messages, retrieve_runs

# 環境変数をロードし、OpenAIクライアントを初期化します。
load_dotenv()
client = OpenAI()
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_ID = os.getenv("THREAD_ID")


def response_chatbot(assistant, thread, user_input):
    """
    ユーザーの入力に基づいてチャットボットの応答を生成し、結果をリストで返します。

    Parameters:
    assistant (Assistant): OpenAI Assistantのインスタンス。
    thread (Thread): OpenAI Threadのインスタンス。
    user_input (str): ユーザーからの入力文字列。

    Returns:
    list: チャットボットの応答メッセージのリスト。
    """
    # ユーザーの入力をスレッドに投稿します。
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_input
    )
    # アシスタントによる応答を生成するためのrunを作成します。
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    # runの完了を待ち、結果を取得します。
    run = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id, max_time=360)
    # スレッド内のメッセージを取得します。
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    # メッセージを変換してわかりやすい形式にします。
    assistant_msg_list = transform_latest_assistant_messages(messages=messages)

    # 応答メッセージをリストに追加します。
    result = []
    for data in assistant_msg_list:
        result.append(f"チャットボット: {data['content']['value']}")
    return result


def main():
    """
    メイン関数。環境変数からアシスタントとスレッドのIDを取得し、
    チャットボットのセッションを開始します。ユーザーの入力に応じて応答を生成し、
    特定のキーワードでセッションを終了します。
    """
    try:
        # ファイルをアシスタントにアップロードします。
        file = client.files.create(
            file=open("./sample_files/manual.pdf", "rb"), purpose="assistants"
        )

        # アシスタントのインスタンスを取得または作成します。
        assistant = (
            client.beta.assistants.retrieve(ASSISTANT_ID)
            if ASSISTANT_ID
            else client.beta.assistants.create(
                instructions="あなたはカスタマーサポートのチャットボットです。ナレッジベースを活用して、顧客からの問い合わせに最適な対応をしましょう。ユーザーには日本語で回答してください。",
                model="gpt-4-1106-preview",
                tools=[{"type": "retrieval"}],
                file_ids=[file.id],
            )
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
            for response_text in res:
                print(response_text)

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
