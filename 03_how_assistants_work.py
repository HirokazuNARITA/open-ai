#!/usr/bin/env python3
from openai import OpenAI
import random
import os
from dotenv import load_dotenv
import traceback
from common.utils import create_and_open_file
from common.helper import retrieve_runs, transform_latest_assistant_messages

# 環境変数をロードします。
load_dotenv()
# OpenAIクライアントを初期化します。
client = OpenAI()

try:
    # アシスタント用のファイルをアップロードします。
    file = client.files.create(
        file=open("./sample_files/Location_v2.csv", "rb"), purpose="assistants"
    )

    # ランダムな番号を生成してアシスタントに名前を付けます。
    random_num = random.randint(1, 100)
    assistant = client.beta.assistants.create(
        name=f"データビジュアライザー_{random_num}号",
        description="あなたは美しいデータビジュアライゼーションを作成するのが得意です。あなたは、.csvファイルに存在するデータを分析し、傾向を理解し、それらの傾向に関連するデータビジュアライゼーションを考え出します。また、観察されたトレンドの簡単なテキストサマリーを共有します。",
        model="gpt-4-1106-preview",
        tools=[{"type": "code_interpreter"}],
        # file_ids=[file.id],  # コメントアウトされた部分は、将来的にファイルをアシスタントに関連付ける場合に使用します。
    )

    # ユーザーからの指示を含むスレッドを作成します。
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

    # アシスタントにタスクを実行させるためのrunを作成します。
    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    # runの完了を待ち、結果を取得します。
    run = retrieve_runs(client=client, thread_id=thread.id, run_id=run.id, max_time=360)
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    # アシスタントからの最新のメッセージを取得し、わかりやすい形式に変換します。
    assistant_msg_list = transform_latest_assistant_messages(messages=messages)

    # ファイルダウンロード機能を定義します。
    def file_download(file_id, file_path):
        data = client.files.content(file_id=file_id)
        data_bytes = data.read()
        with create_and_open_file(filepath=file_path, mode="wb") as file:
            file.write(data_bytes)

    # アシスタントからの最新のメッセージを表示し、関連するファイルをダウンロードします。
    for data in assistant_msg_list:
        content = data["content"]
        id = data["id"]
        print(content["value"])
        print(",".join(content["image_file_ids"]) if content["image_file_ids"] else "")
        print(
            ",".join(map(lambda x: x["file_id"], content["file_ids"]))
            if content["file_ids"]
            else ""
        )

        # 画像ファイルをダウンロードします。
        for image_file_id in content["image_file_ids"]:
            image_file_path = os.path.join(f"./output/{id}", image_file_id + ".png")
            file_download(file_id=image_file_id, file_path=image_file_path)
        # 注釈用ファイルをダウンロードします。
        for file_info in content["file_ids"]:
            file_id = file_info["file_id"]
            file_ext = file_info["ext"]
            file_path = os.path.join(f"./output/{id}", f"{file_id}.{file_ext}")
            file_download(file_id=file_id, file_path=file_path)

# 例外が発生した場合にエラー情報を出力し、最終的にアシスタント、ファイル、スレッドを削除するためのクリーンアップ処理を行います。
except Exception as e:
    print("予期せぬエラーが発生しました:", e)
    print(traceback.print_exc())

finally:
    # アシスタントの削除
    if assistant:
        result_del_assistant = client.beta.assistants.delete(assistant.id)
        print(result_del_assistant)
    # ファイルの削除
    if file:
        result_del_file = client.files.delete(file_id=file.id)
        print(result_del_file)
    # スレッドの削除
    if thread:
        result_del_thread = client.beta.threads.delete(thread.id)
        print(result_del_thread)
