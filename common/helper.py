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

        # contentを走査し、インスタンスによって異なる辞書を定義する
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

        ## textとimageを同じ辞書に設定する
        if text_content:
            text_content["images_file_ids"] = image_file_ids
            transformed_data.append({"content": text_content})
        else:
            # TextContentがない場合（通常はないが、念のため）
            for image_file_id in image_file_ids:
                transformed_data.append(
                    {"content": {"type": "image", "file_id": image_file_id}}
                )
    return transformed_data
