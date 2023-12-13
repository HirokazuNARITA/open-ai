#!/usr/bin/env python3
from openai import OpenAI
import random
import pprint
import os
import traceback
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
)
from common.utils import retrieve_runs
from common.helper import transform_latest_assistant_messages, create_and_open_file

client = OpenAI()

try:
    file = client.files.create(
        file=open("./sample_files/Location_v2.csv", "rb"), purpose="assistants"
    )

    random_num = random.randint(1, 100)
    assistant = client.beta.assistants.create(
        name=f"データビジュアライザー_{random_num}号",
        description="あなたは美しいデータビジュアライゼーションを作成するのが得意です。あなたは、.csvファイルに存在するデータを分析し、傾向を理解し、それらの傾向に関連するデータビジュアライゼーションを考え出します。また、観察されたトレンドの簡単なテキストサマリーを共有します。",
        model="gpt-4-1106-preview",
        tools=[{"type": "code_interpreter"}],
        # file_ids=[file.id],
    )

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "このファイルの傾向に基づいて、3つのデータ可視化を作成する。",
                "file_ids": [file.id],
            }
        ]
    )
    print("-----thread-----")
    print(vars(thread))

    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    run = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id, max_time=360)
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    # assistantの最新レス群を辞書形式で取得（messages直だとすごくわかりにくい）
    assistant_msg_list = transform_latest_assistant_messages(messages=messages)

    # ファイルダウンロードをローカル関数化
    def file_download(file_id, file_path):
        data = client.files.content(file_id=file_id)
        data_bytes = data.read()
        with create_and_open_file(filepath=file_path, mode="wb") as file:
            file.write(data_bytes)

    # assistantの最新レス群を表示とダウンロード
    for data in assistant_msg_list:
        content = data["content"]
        id = data["id"]
        print(content["value"])
        print(",".join(content["image_file_ids"]) if content["image_file_ids"] else "")
        print(",".join(content["file_ids"]) if content["file_ids"] else "")

        # 画像ファイルのダウンロード
        for image_file_id in content["image_file_ids"]:
            image_file_path = os.path.join(f"./output/{id}", image_file_id + ".png")
            file_download(file_id=image_file_id, file_path=image_file_path)
        # 注釈ファイルのダウンロード
        for file_info in content["file_ids"]:
            file_id = file_info["file_id"]
            file_ext = file_info["ext"]
            file_path = os.path.join(f"./output/{id}", f"{file_id}.{file_ext}")
            file_download(file_id=file_id, file_path=file_path)


except Exception as e:
    print("予期せぬエラーが発生しました:", e)
    print(traceback.print_exc())

finally:
    if assistant:
        result_del_assistant = client.beta.assistants.delete(assistant.id)
        print(result_del_assistant)
    if file:
        result_del_file = client.files.delete(file_id=file.id)
        print(result_del_file)
    if thread:
        result_del_thread = client.beta.threads.delete(thread.id)
        print(result_del_thread)
