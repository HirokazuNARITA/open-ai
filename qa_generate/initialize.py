import sys
import os

# 現在のファイルのパスからプロジェクトのルートパスを取得してsys.pathに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from openai import OpenAI
from common.utils import update_env_file
from common.helper import retrieve_runs
from dotenv import load_dotenv

load_dotenv(override=True)
client = OpenAI()

ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_ID = os.getenv("THREAD_ID")
FILE_ID = os.getenv("FILE_ID")


def main():
    if ASSISTANT_ID:
        client.beta.assistants.delete(assistant_id=ASSISTANT_ID)
        update_env_file(
            env_file_path=".env", key_to_update="ASSISTANT_ID", new_value=""
        )
    if THREAD_ID:
        client.beta.threads.delete(thread_id=THREAD_ID)
        update_env_file(env_file_path=".env", key_to_update="THREAD_ID", new_value="")

    if FILE_ID:
        client.files.delete(file_id=FILE_ID)
        update_env_file(env_file_path=".env", key_to_update="FILE_ID", new_value="")

    file = client.files.create(
        file=open("../sample_files/manual.pdf", "rb"), purpose="assistants"
    )

    assistant = client.beta.assistants.create(
        instructions="あなたは資料を参照してその内容について処理をするアシスタントボットです。",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}],
        file_ids=[file.id],
    )

    thread = client.beta.threads.create()

    update_env_file(env_file_path=".env", key_to_update="FILE_ID", new_value=file.id)
    update_env_file(
        env_file_path=".env", key_to_update="ASSISTANT_ID", new_value=assistant.id
    )
    update_env_file(
        env_file_path=".env", key_to_update="THREAD_ID", new_value=thread.id
    )

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="与えられた資料を一通り読み込み、内容を理解し、回答できるようになったら「完了」とのみ回答しなさい。",
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    run = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id, max_time=120)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print(messages)


if __name__ == "__main__":
    main()
