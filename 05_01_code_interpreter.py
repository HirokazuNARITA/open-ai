import traceback
from openai import OpenAI
from dotenv import load_dotenv
from common.helper import StreamingEventHandler

load_dotenv(override=True)
client = OpenAI()

assistant = None
thread = None
file = None

try:
    # ・コードインタプリタの有効化
    # assistantのinstructionsに「この問題を解決するコードを書いてください」などを指定することによりCode_interpreterの実行を促進できます。
    assistant = client.beta.assistants.create(
        name="数学の家庭教師",
        instructions="あなたは数学の家庭教師です。数学の質問をされたら、その質問に答えるコードを書いて実行し、質問に答えてください。",
        model="gpt-4-turbo",
        tools=[{"type": "code_interpreter"}],
    )

    thread = client.beta.threads.create()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="方程式 `3x + 11 = 14` を解きたいのですが、教えてくれますか？",
    )

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        event_handler=StreamingEventHandler(),
    ) as stream:
        stream.until_done()


except Exception as e:
    print("予期せぬエラーが発生しました。", {e})
    print(traceback.print_exc())
finally:
    if thread:
        result_del_thread = client.beta.threads.delete(thread_id=thread.id)
        print(result_del_thread)
    if assistant:
        result_del_assistant = client.beta.assistants.delete(assistant_id=assistant.id)
        print(result_del_assistant)
    if file:
        result_del_file = client.files.delete(file_id=file.id)
        print(result_del_file)
