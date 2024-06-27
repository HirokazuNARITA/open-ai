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

from openai import AssistantEventHandler
from typing_extensions import override
import ast

# 環境変数をロードします。
load_dotenv(override=True)
# OpenAIクライアントを初期化します。
client = OpenAI()


def get_current_temperature(location, unit="c"):
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


def get_rain_probability(location):
    """
    指定された場所の降水確率を取得します。

    Parameters:
    location (str): 降水確率を取得する場所。

    Returns:
    str: 降水確率を示す文字列。
    """
    return "0.5"


def call_function_by_name(function_name, args_dict):
    # グローバルスコープで関数名の文字列から関数を取得して実行
    args = ast.literal_eval(args_dict)
    function = globals()[function_name]
    return function(**args)


class EventHandler(AssistantEventHandler):
    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == "thread.run.requires_action":
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        for tool in data.required_action.submit_tool_outputs.tool_calls:
            result = call_function_by_name(tool.function.name, tool.function.arguments)
            tool_outputs.append({"tool_call_id": tool.id, "output": result})

            # if tool.function.name == "get_current_temperature":
            #     tool_outputs.append({"tool_call_id": tool.id, "output": "57"})
            # elif tool.function.name == "get_rain_probability":
            #     tool_outputs.append({"tool_call_id": tool.id, "output": "0.06"})

        # Submit all tool_outputs at the same time
        self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
        # Use the submit_tool_outputs_stream helper
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,  # type: ignore
            run_id=self.current_run.id,  # type: ignore
            tool_outputs=tool_outputs,
            event_handler=EventHandler(),
        ) as stream:
            for text in stream.text_deltas:
                print(text, end="", flush=True)
            print()


def main():
    """
    メイン関数。天気ボットとして機能するアシスタントを作成し、
    ユーザーからのリクエストに応じて天気情報と都市のニックネームを提供します。
    """
    assistant = None
    thread = None

    try:
        # アシスタントを作成します。
        assistant = client.beta.assistants.create(
            instructions="You are a weather bot. Use the provided functions to answer questions.",
            model="gpt-4o",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_current_temperature",
                        "description": "Get the current temperature for a specific location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state, e.g., San Francisco, CA",
                                },
                                "unit": {
                                    "type": "string",
                                    "enum": ["Celsius", "Fahrenheit"],
                                    "description": "The temperature unit to use. Infer this from the user's location.",
                                },
                            },
                            "required": ["location", "unit"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_rain_probability",
                        "description": "Get the probability of rain for a specific location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state, e.g., San Francisco, CA",
                                }
                            },
                            "required": ["location"],
                        },
                    },
                },
            ],
        )

        # スレッドを作成し、ユーザーのメッセージを投稿します。
        thread = client.beta.threads.create()
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="What's the weather in San Francisco today and the likelihood it'll rain?",
        )

        with client.beta.threads.runs.stream(
            thread_id=thread.id, assistant_id=assistant.id, event_handler=EventHandler()
        ) as stream:
            stream.until_done()

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
