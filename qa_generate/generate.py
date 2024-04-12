import sys
import os

# 現在のファイルのパスからプロジェクトのルートパスを取得してsys.pathに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from openai import OpenAI
from dotenv import load_dotenv
import json

from common.helper import retrieve_runs, transform_latest_assistant_messages

load_dotenv(override=True)
client = OpenAI()

ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_ID = os.getenv("THREAD_ID")
FILE_ID = os.getenv("FILE_ID")


def transport_qa_data(qa_data):
    print(json.dumps(qa_data, indent=2, ensure_ascii=False))
    return "OK"


def main():

    client.beta.assistants.update(
        assistant_id=ASSISTANT_ID,
        instructions=f"""
You are an assistant tasked with creating anticipated questions and answers after reading a document. 
Create the questions and answers, and use the tool transport_qa_data to transfer them to an external system. 
You will be instructed on the number of questions and answers to create, so produce that number and transfer the data to the external system. 
Please create the data in Japanese.
Respond only with confirmation of the transfer to the user.
""",
        file_ids=[FILE_ID],
        tools=[
            {"type": "retrieval"},
            {
                "type": "function",
                "function": {
                    "name": "transport_qa_data",
                    "description": "質問と回答のペアデータを外部システムに転送する。",
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
                                            "description": "質問の内容",
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
    )

    client.beta.threads.messages.create(
        thread_id=THREAD_ID,
        role="user",
        content="文書に関するQAを新規に10件作成してください",
    )

    run = client.beta.threads.runs.create(
        thread_id=THREAD_ID,
        assistant_id=ASSISTANT_ID,
    )

    run = retrieve_runs(client=client, thread_id=THREAD_ID, run_id=run.id, max_time=240)

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
            thread_id=THREAD_ID, run_id=run.id, tool_outputs=tool_outputs
        )

        run = retrieve_runs(
            client=client, thread_id=THREAD_ID, run_id=run.id, max_time=120
        )

        print(run)

    messages = client.beta.threads.messages.list(thread_id=THREAD_ID)
    result = transform_latest_assistant_messages(messages=messages)

    for message in result:
        print(message["content"]["value"])


if __name__ == "__main__":
    main()
