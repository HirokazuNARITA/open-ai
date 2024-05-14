#!/usr/bin/env python3
import traceback
from openai import OpenAI
from dotenv import load_dotenv
from common.helper import StreamingEventHandler


# 環境変数をロードします。
load_dotenv(override=True)
# OpenAIクライアントを初期化します。
client = OpenAI()

assistant = None
thread = None

try:
    # 数学の家庭教師アシスタントを作成します。
    assistant = client.beta.assistants.create(
        name="数学の家庭教師",
        description="あなたは数学の家庭教師です。コードを書いて実行し、数学の質問に答えてください。",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4o",
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
        # content="方程式 `3x + 11 = 14` を解きたいのですが、教えてくれますか？",
        content="`f(x,y)=x^2+2xy+2y^2−6x+4y−1`の最小値を計算したいのですが、教えてくれますか？",
    )
    print("-------messageの生成---------")
    print(message)

    # ### streamingなし ####
    # # runの詳細を取得します。
    # run = client.beta.threads.runs.create_and_poll(
    #     thread_id=thread.id,
    #     assistant_id=assistant.id,
    #     # instructions="Please address the user as Jane Doe. The user has a premium account.",
    # )

    # if run.status == "completed":
    #     # スレッド内のメッセージをリストアップします。
    #     messages = client.beta.threads.messages.list(thread_id=thread.id)
    #     print("--------messagesのリストアップ-------")
    #     print(messages)

    #     # アシスタントからの最新の回答を取得します。
    #     latest_assistant_response = next(
    #         (m.content[0].text.value for m in messages.data if m.role == "assistant"), None  # type: ignore
    #     )
    #     print("-----Assistantの最新の回答-----")
    #     print(latest_assistant_response)
    # else:
    #     print("-----Assistantの回答失敗-----")
    #     print(f"回答に失敗しました。runステータス:{run.status}")
    # ### streamingなし ###

    ### streaingあり ###
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        event_handler=StreamingEventHandler(),
    ) as stream:
        stream.until_done()
    ### streaingあり ###

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
