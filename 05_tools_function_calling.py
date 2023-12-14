#!/usr/bin/env python3
from openai import OpenAI
import os
import traceback
import pprint
import json
from dotenv import load_dotenv
from common.utils import update_env_file
from common.helper import (
    transform_latest_assistant_messages,
    retrieve_runs,
    latest_messages_from_assistant,
)

client = OpenAI()


def getCurrentWeather(location, unit="c"):
    val = "22" if unit == "c" else "71.6"
    return f"{val}{unit}"


def getNickname(location):
    return "LA"


def main():
    try:
        file = None

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
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread.id,
            role="user",
            content="I am in Los Angeles now. Please tell me the weather and City's Nickname.",
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        run = retrieve_runs(
            client=client, thread_id=thread.id, run_id=run.id, max_time=360
        )

        if run.required_action:
            tool_outputs = []
            for required_action in run.required_action.submit_tool_outputs.tool_calls:
                tool_call_id = required_action.id
                func_name = required_action.function.name
                args_str = required_action.function.arguments
                args_dict = json.loads(args_str)

                result = globals()[func_name](**args_dict)
                tool_outputs.append(
                    {
                        "tool_call_id": tool_call_id,
                        "output": result,
                    }
                )

            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )

            run = retrieve_runs(
                client=client, thread_id=thread.id, run_id=run.id, max_time=360
            )

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        result = transform_latest_assistant_messages(messages=messages)
        for message in result:
            print(message["content"]["value"])

    except Exception as e:
        print("予期せぬエラーが発生しました:", e)
        print(traceback.print_exc())
    finally:
        if assistant:
            result_del_assistant = client.beta.assistants.delete(assistant.id)
            print(result_del_assistant)
        if thread:
            result_del_thread = client.beta.threads.delete(thread.id)
            print(result_del_thread)


if __name__ == "__main__":
    main()
