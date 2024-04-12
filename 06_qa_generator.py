from openai import OpenAI
from dotenv import load_dotenv
import traceback
import json
import os
from common.helper import retrieve_runs, transform_latest_assistant_messages
from common.utils import update_env_file

load_dotenv(override=True)
client = OpenAI()

ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_ID = os.getenv("THREAD_ID")
FILE_ID = os.getenv("FILE_ID")


def transport_qa_data(qa_data):
    print(json.dumps(qa_data, indent=2, ensure_ascii=False))
    return "OK"


def main():
    file = None
    assistant = None
    thread = None

    try:
        file = (
            client.files.retrieve(file_id=FILE_ID)
            if FILE_ID
            else client.files.create(
                file=open("./sample_files/manual.pdf", "rb"), purpose="assistants"
            )
        )
        update_env_file(
            env_file_path=".env", key_to_update="FILE_ID", new_value=file.id
        )

        thread = (
            client.beta.threads.retrieve(thread_id=THREAD_ID)
            if THREAD_ID
            else client.beta.threads.create()
        )
        update_env_file(
            env_file_path=".env", key_to_update="THREAD_ID", new_value=thread.id
        )

        assistant = (
            client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
            if ASSISTANT_ID
            else client.beta.assistants.create(
                name="QA作成アシスタント",
                instructions="""
あなたは資料を読んで想定される質問と回答を作成するためのアシスタントです。
質問と回答を作成しツール`transport_qa_data`を使用して外部システムに転送します。
ユーザーから質問と回答を作成する件数の指示がありますので、その件数分作成し、データを外部システムに転送てください。
必ず転送を実施し、結果を応答してください。
プログラム上での動作を想定しているため、同じことを何度も依頼されても、作業を省略せず一からやり直してください。
何度もお願いすることになって申し訳ないのですが、がんばってください。
""",
                model="gpt-4-turbo-preview",
                tools=[
                    {"type": "retrieval"},
                    {
                        "type": "function",
                        "function": {
                            "name": "transport_qa_data",
                            "description": "作成した質問と回答のペアデータを外部システムに転送する。",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "qa_data": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "question": {
                                                    "type": "string",
                                                    "description": "作成した質問の内容",
                                                },
                                                "answer": {
                                                    "type": "string",
                                                    "description": "questionに対する回答の内容",
                                                },
                                            },
                                            "required": ["question", "answer"],
                                        },
                                    }
                                },
                                "required": ["qa_data"],
                            },
                        },
                    },
                ],
                file_ids=[file.id],
            )
        )
        update_env_file(
            env_file_path=".env", key_to_update="ASSISTANT_ID", new_value=assistant.id
        )

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="新規に10件のQAを作成し、外部システムに転送しなさい",
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=assistant.id
        )

        run = retrieve_runs(
            client=client, thread_id=thread.id, run_id=run.id, max_time=240
        )

        if run.required_action:
            tool_outputs = []
            for required_action in run.required_action.submit_tool_outputs.tool_calls:
                tool_call_id = required_action.id
                func_name = required_action.function.name
                args_str = required_action.function.arguments
                args_dict = json.loads(args_str)

                result = globals()[func_name](**args_dict)
                tool_outputs.append({"tool_call_id": tool_call_id, "output": result})

            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )

            run = retrieve_runs(
                client=client, thread_id=thread.id, run_id=run.id, max_time=120
            )

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        result = transform_latest_assistant_messages(messages=messages)

        for message in result:
            print(message["content"]["value"])

    except Exception as e:
        print("エラーが発生しました。", e)
        print(traceback.print_exc())
    # finally:
    # if assistant:
    #     result_assistant_delete = client.beta.assistants.delete(
    #         assistant_id=assistant.id
    #     )
    #     print(result_assistant_delete)
    # if thread:
    #     result_thread_delete = client.beta.threads.delete(thread_id=thread.id)
    #     print(result_thread_delete)


if __name__ == "__main__":
    main()
