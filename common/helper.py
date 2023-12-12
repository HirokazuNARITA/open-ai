import os
from openai import OpenAI
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
)
from common.utils import latest_messages_from_assistant


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
