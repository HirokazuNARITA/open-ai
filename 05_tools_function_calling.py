#!/usr/bin/env python3
from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv
import pprint
import json
from dotenv import load_dotenv
from common.utils import update_env_file
from common.helper import (
    transform_latest_assistant_messages,
    retrieve_runs,
    latest_messages_from_assistant,
)

# 環境変数をロードします。
load_dotenv()
# OpenAIクライアントを初期化します。
client = OpenAI()


def getCurrentWeather(location, unit="c"):
    """
    指定された場所の現在の天気を取得します。

    Parameters:
    location (str): 天気を取得する場所。
    unit (str): 温度の単位（'c' または 'f'）。

    Returns:
    str: 温度と単位を含む文字列。
    """
    val = "22" if unit == "c" else "71.6"
    return f"{val}{unit}"


def getNickname(location):
    """
    指定された場所のニックネームを取得します。

    Parameters:
    location (str): ニックネームを取得する場所。

    Returns:
    str: 場所のニックネーム。
    """
    return "LA"


def main():
    """
    メイン関数。天気ボットとして機能するアシスタントを作成し、
    ユーザーからのリクエストに応じて天気情報と都市のニックネームを提供します。
    """
    try:
        # アシスタントを作成します。
        assistant = client.beta.assistants.create(
            instructions="You are a weather bot. Use the provided functions to answer questions. Use nicknames to answer the city name.",
            model="gpt-4-1106-preview",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "getCurrentWeather",
                        "description": "Get the weather in location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state e.g. San Francisco, CA",
                                },
                                "unit": {"type": "string", "enum": ["c", "f"]},
                            },
                        },
                        "required": ["location"],
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "getNickname",
                        "description": "Get the nickname of a city",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state e.g. San Francisco, CA",
                                },
                            },
                        },
                        "required": ["location"],
                    },
                },
            ],
        )

        # スレッドを作成し、ユーザーのメッセージを投稿します。
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread.id,
            role="user",
            content="I am in Los Angeles now. Please tell me the weather and City's Nickname.",
        )

        # アシスタントにタスクを実行させるためのrunを作成します。
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        # runの完了を待ち、結果を取得します。
        run = retrieve_runs(
            client=client, thread_id=thread.id, run_id=run.id, max_time=360
        )

        # 必要なアクションがある場合は、ツールの出力を処理します。
        if run.required_action:
            tool_outputs = []
            for required_action in run.required_action.submit_tool_outputs.tool_calls:
                tool_call_id = required_action.id
                func_name = required_action.function.name
                args_str = required_action.function.arguments
                args_dict = json.loads(args_str)

                # 関数を実行し、結果を取得します。
                result = globals()[func_name](**args_dict)
                tool_outputs.append(
                    {
                        "tool_call_id": tool_call_id,
                        "output": result,
                    }
                )

            # ツールの出力をsubmitします。
            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )

            # runの完了を再度待ち、最終結果を取得します。
            run = retrieve_runs(
                client=client, thread_id=thread.id, run_id=run.id, max_time=360
            )

        # スレッド内のメッセージを取得し、変換します。
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        result = transform_latest_assistant_messages(messages=messages)
        # 結果を出力します。
        for message in result:
            print(message["content"]["value"])

    except Exception as e:
        # 予期せぬエラーが発生した場合のエラーメッセージを出力します。
        print("予期せぬエラーが発生しました:", e)
        print(traceback.print_exc())
    finally:
        # アシスタントとスレッドを削除するクリーンアップ処理を行います。
        if assistant:
            result_del_assistant = client.beta.assistants.delete(assistant.id)
            print(result_del_assistant)
        if thread:
            result_del_thread = client.beta.threads.delete(thread.id)
            print(result_del_thread)


# メイン関数を実行します。
if __name__ == "__main__":
    main()
