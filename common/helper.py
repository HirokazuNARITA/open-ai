import os
from openai import OpenAI
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
)
import backoff
import requests


def _retrieve_runs(client, thread_id, run_id):
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

    print("running.....")

    if run.status == "completed":
        # print("Runが完了しました。")
        return run
    elif run.status == "failed":
        print("Runが失敗しました。")
        return run
    elif run.status == "expired":
        print("Runが期限切れになりました。")
        return run

    # まだ完了していない場合は例外を発生させてリトライ
    raise requests.exceptions.RequestException("Runはまだ完了していません。")


def retrieve_runs(client, thread_id, run_id, max_time=30):
    # backoffデコレータを動的に適用
    backoff_decorator = backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=max_time
    )
    wrapped_function = backoff_decorator(_retrieve_runs)
    return wrapped_function(client, thread_id, run_id)


def latest_messages_from_assistant(messages):
    latest_assistant_data = []

    # 最初に見つかった role="user" の位置を見つける
    user_index = next(
        (i for i, m in enumerate(messages.data) if m.role == "user"), None
    )
    # role="user" 以前の role="assistant" のデータを取り出す
    if user_index is not None:
        latest_assistant_data = [
            item for item in messages.data[:user_index] if item.role == "assistant"
        ]

    return latest_assistant_data


def transform_latest_assistant_messages(messages):
    latest_assistant_data = latest_messages_from_assistant(messages=messages)
    transformed_data = []
    for item in latest_assistant_data:
        text_content = None
        image_file_ids = []
        id = item.id

        # contentを走査し、インスタンスによって異なる辞書を定義する
        for content in item.content:
            if isinstance(content, MessageContentText):
                # MessageContentText の場合
                text_info = content.text.value
                file_paths = [
                    {
                        "file_id": annotation.file_path.file_id,
                        "ext": os.path.splitext(annotation.text)[1][1:],  # 拡張子を抽出
                    }
                    for annotation in content.text.annotations
                    # if isinstance(annotation, TextAnnotationFilePath)
                ]
                text_content = {
                    "type": "text",
                    "value": text_info,
                    "file_ids": file_paths,
                }
            elif isinstance(content, MessageContentImageFile):
                # MessageContentImageFile の場合
                image_file_ids.append(content.image_file.file_id)

        ## textとimageを同じ辞書に設定する
        if text_content:
            text_content["image_file_ids"] = image_file_ids
            transformed_data.append({"id": id, "content": text_content})
        else:
            # TextContentがない場合（通常はないが、念のため）
            for image_file_id in image_file_ids:
                transformed_data.append(
                    {
                        "id": id,
                        "content": {
                            "type": "image",
                            "image_file_ids": [image_file_id],
                        },
                    }
                )
    return transformed_data[::-1]


def create_and_open_file(filepath, mode="w"):
    # ファイルのディレクトリ部分を取得
    directory = os.path.dirname(filepath)

    # ディレクトリが存在しない場合は作成
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # ファイルをオープン
    return open(filepath, mode)


def update_env_file(env_file_path, key_to_update, new_value):
    # .envファイルを読み込む
    with open(env_file_path, "r") as file:
        lines = file.readlines()

    # 更新するキーを探し、値を変更する
    updated_lines = []
    key_found = False
    for line in lines:
        if line.startswith(key_to_update + "="):
            updated_lines.append(f"{key_to_update}={new_value}\n")
            key_found = True
        else:
            updated_lines.append(line)

    # キーが存在しない場合は追加
    if not key_found:
        updated_lines.append(f"{key_to_update}={new_value}\n")

    # 変更をファイルに書き戻す
    with open(env_file_path, "w") as file:
        file.writelines(updated_lines)
