#!/usr/bin/env python3
import traceback
from openai import OpenAI
from dotenv import load_dotenv
from common.helper import EventHandler


# 環境変数をロードします。
load_dotenv()
# OpenAIクライアントを初期化します。
client = OpenAI(default_headers={"OpenAI-Beta": "assistants=v1"})

assistant = None
thread = None


try:
    # 数学の家庭教師アシスタントを作成します。
    assistant = client.beta.assistants.create(
        name="数学の家庭教師",
        description="あなたは数学の家庭教師です。コードを書いて実行し、数学の質問に答えてください。",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4-turbo-2024-04-09",
    )
    print("-----assistantの生成-------")
    print(assistant)

    # 新しいスレッドを作成します。
    thread = client.beta.threads.create()
    print("------threadの生成---------")
    print(thread)

    # スレッドにユーザーのメッセージを投稿します。
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="方程式 `3x + 9 = 14` を解きたいのですが、教えてくれますか？",
    )
    print("-------messageの生成---------")
    print(message)

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        # instructions="Please address the user as Jane Doe. The user has a premium account.",
        # event_handler=EventHandler(),
    ) as stream:
        # stream.until_done()
        for text in stream.text_deltas:
            print(text, end="", flush=True)
        print("")

    # # アシスタントに指示を出すためのrunを作成します。
    # run = client.beta.threads.runs.create(
    #     thread_id=thread.id,
    #     assistant_id=assistant.id,
    #     # instructions="ユーザー名を 成田 浩和 としてください。このユーザーはプレミアムアカウントを持っています。",
    # )
    # print("------runの生成--------")
    # print(run)

    # # runの詳細を取得します。
    # run_details = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id)
    # print("-----runの詳細-----")
    # print(run_details)

    # # スレッド内のメッセージをリストアップします。
    # messages = client.beta.threads.messages.list(thread_id=thread.id)
    # print("--------messagesのリストアップ-------")
    # print(messages)

    # # アシスタントからの最新の回答を取得します。
    # latest_assistant_response = next(
    #     (m.content[0].text.value for m in messages.data if m.role == "assistant"), None  # type: ignore
    # )
    # print("-----Assistantの最新の回答-----")
    # print(
    #     latest_assistant_response
    #     if latest_assistant_response is not None
    #     else "回答が見つかりませんでした。"
    # )

except Exception as e:
    # 予期せぬエラーが発生した場合の処理を行います。
    print("予期せぬエラーが発生しました:", {e})
    print(traceback.print_exc())

finally:
    # スレッドとアシスタントを削除するクリーンアップ処理を行います。
    if thread:
        result_del = client.beta.threads.delete(thread.id)
        print(result_del)

    if assistant:
        result_del_assistant = client.beta.assistants.delete(assistant.id)
        print(result_del_assistant)
