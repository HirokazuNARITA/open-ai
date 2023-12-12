#!/usr/bin/env python3
import traceback
from openai import OpenAI
from common.utils import retrieve_runs

client = OpenAI()

try:
    assistant = client.beta.assistants.create(
        name="数学の家庭教師",
        description="あなたは数学の家庭教師です。コードを書いて実行し、数学の質問に答えてください。",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4-1106-preview",
    )
    print("-----assistantの生成-------")
    print(assistant)

    thread = client.beta.threads.create()
    print("------threadの生成---------")
    print(thread)

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="方程式 `3x + 11 = 14` を解きたいのですが、教えてくれますか？",
    )
    print("-------messageの生成---------")
    print(message)

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="ユーザー名を 成田 浩和 としてください。このユーザーはプレミアムアカウントを持っています。",
    )

    print("------runの生成--------")
    print(run)

    run = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id)
    print("-----runの回収-----")
    print(run)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print("--------messagesのリストアップ-------")
    print(messages)

    # messagesリストからassistantの最新の回答を抽出
    latest_assistant_response = next(
        (m.content[0].text.value for m in messages.data if m.role == "assistant"), None
    )
    print("-----Assistantの最新の回答-----")
    print(
        latest_assistant_response
        if latest_assistant_response is not None
        else "回答が見つかりませんでした。"
    )


except Exception as e:
    print("予期せぬエラーが発生しました:", {e})
    print(traceback.print_exc())

finally:
    # 後片付け
    if thread:
        result_del = client.beta.threads.delete(thread.id)
        print(result_del)

    if assistant:
        result_del_assistant = client.beta.assistants.delete(assistant.id)
        print(result_del_assistant)
