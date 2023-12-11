#!/usr/bin/env python3
from openai import OpenAI
import random
import pprint
import os
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
)
from common.utils import retreve_runs

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
        file_ids=[file.id],
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

    run = retreve_runs(client=client, thread_id=thread.id, run_id=run.id)
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    # assistantの最新レス群
    ## 最初に見つかった role="user" の位置を見つける
    user_index = next(
        (i for i, m in enumerate(messages.data) if m.role == "user"), None
    )
    ## role="user" 以前の role="assistant" のデータを取り出す
    if user_index is not None:
        latest_assistant_data = [
            item for item in messages.data[:user_index] if item.role == "assistant"
        ]
    else:
        latest_assistant_data = []
    # pprint.pprint(latest_assistant_data)

    # 変換
    # transformed_data = []
    # for item in latest_assistant_data:
    #     transformed_content = []
    #     for content in item.content:
    #         if isinstance(content, MessageContentText):
    #             # MessageContentText の場合
    #             text_info = content.text.value
    #             file_paths = [
    #                 annotation.file_path.file_id
    #                 for annotation in content.text.annotations
    #                 # if isinstance(annotation, TextAnnotationFilePath)
    #             ]
    #             transformed_content.append(
    #                 {"type": "text", "value": text_info[:10], "file_ids": file_paths}
    #             )
    #         elif isinstance(content, MessageContentImageFile):
    #             # MessageContentImageFile の場合
    #             file_id = content.image_file.file_id
    #             transformed_content.append({"type": "image", "file_id": file_id})
    #     transformed_data.append({"content": transformed_content})

    transformed_data = []

    for item in latest_assistant_data:
        text_content = None
        image_file_ids = []

        for content in item.content:
            if isinstance(content, MessageContentText):
                # MessageContentText の場合
                text_info = content.text.value[:10]
                file_paths = [
                    {
                        "type": "image",
                        "file_id": annotation.file_path.file_id,
                        "ext": os.path.splitext(annotation.text)[1][1:],  # 拡張子を抽出
                    }
                    for annotation in content.text.annotations
                    # if isinstance(annotation, TextAnnotationFilePath)
                ]
                text_content = {
                    "value": text_info,
                    "file_ids": file_paths,
                }
            elif isinstance(content, MessageContentImageFile):
                # MessageContentImageFile の場合
                image_file_ids.append(content.image_file.file_id)

        if text_content:
            text_content["images_file_ids"] = image_file_ids
            transformed_data.append({"content": text_content})
        else:
            # TextContentがない場合（通常はないが、念のため）
            for image_file_id in image_file_ids:
                transformed_data.append(
                    {"content": {"type": "image", "file_id": image_file_id}}
                )

    print(transformed_data)


except Exception as e:
    print("予期せぬエラーが発生しました:", e)

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
