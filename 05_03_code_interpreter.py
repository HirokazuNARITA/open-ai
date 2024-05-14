import traceback
import os
import contextlib
from openai import OpenAI
from dotenv import load_dotenv
from common.helper import StreamingEventHandler, file_download

load_dotenv(override=True)
client = OpenAI()

assistant = None
thread = None
files = []

try:
    # ・ファイルをコードインタープリターに渡す
    with contextlib.ExitStack() as stack:
        file1 = client.files.create(
            file=stack.enter_context(open("./sample_files/test_result1.csv", "rb")),
            purpose="assistants",
        )
        files.append(file1)
        file2 = client.files.create(
            file=stack.enter_context(open("./sample_files/test_result2.csv", "rb")),
            purpose="assistants",
        )
        files.append(file2)

    assistant = client.beta.assistants.create(
        name="数学の家庭教師",
        instructions="あなたは数学の家庭教師です。数学の質問をされたら、その質問に答えるコードを書いて実行し、質問に答えてください。",
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}],
        tool_resources={"code_interpreter": {"file_ids": [files[0].id]}},
    )

    thread = client.beta.threads.create()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="すべてのCSVファイルに含まれるデータについて答えてください。科目ごとの平均点の棒グラフを作成してください。グラフは英語で、可視化の際はmatplotlib.pyplotを使用してください。",
        attachments=[{"file_id": files[1].id, "tools": [{"type": "code_interpreter"}]}],
    )

    Eventhandler = StreamingEventHandler()
    with client.beta.threads.runs.stream(
        thread_id=thread.id, assistant_id=assistant.id, event_handler=Eventhandler
    ) as stream:
        stream.until_done()

    # 画像ファイルをダウンロードします。
    for image_file_id in Eventhandler.file_ids:
        image_file_path = os.path.join(f"./output/{thread.id}", image_file_id + ".png")
        file_download(file_id=image_file_id, file_path=image_file_path)


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
    if len(files) > 0:
        for file in files:
            result_del_file = client.files.delete(file_id=file.id)
            print(result_del_file)
