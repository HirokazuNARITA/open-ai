import os
from openai import OpenAI
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
)
import backoff
import requests


# TextAnnotationFilePath
def _retrieve_runs(client, thread_id, run_id):
    """
    指定されたrunの状態を取得し、完了しているかどうかをチェックします。
    完了していない場合は例外を発生させ、リトライのトリガーとします。

    Parameters:
    client (OpenAI): OpenAIクライアント。
    thread_id (str): スレッドのID。
    run_id (str): runのID。

    Returns:
    Run: 取得したrunのオブジェクト。
    """
    # runの状態を取得
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

    print("running.....")

    # runの状態に応じた処理
    if run.status in ["completed", "requires_action"]:
        return run
    elif run.status == "failed":
        print("Runが失敗しました。")
        return run
    elif run.status == "expired":
        print("Runが期限切れになりました。")
        return run

    # runが完了していない場合は例外を発生
    raise requests.exceptions.RequestException("Runはまだ完了していません。")


def retrieve_runs(client, thread_id, run_id, max_time=30):
    """
    指定されたrunの状態を取得し、必要に応じてリトライを行います。

    Parameters:
    client (OpenAI): OpenAIクライアント。
    thread_id (str): スレッドのID。
    run_id (str): runのID。
    max_time (int): リトライの最大時間（秒）。デフォルトは30秒。

    Returns:
    Run: 取得したrunのオブジェクト。
    """
    # backoffデコレータを動的に適用してリトライ処理を行う
    backoff_decorator = backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=max_time
    )
    # デコレータを適用した関数をラップ
    wrapped_function = backoff_decorator(_retrieve_runs)
    # ラップされた関数を実行
    return wrapped_function(client, thread_id, run_id)


def latest_messages_from_assistant(messages):
    """
    アシスタントからの最新のメッセージを取得します。

    Parameters:
    messages (Messages): スレッド内のメッセージリスト。

    Returns:
    list: アシスタントからの最新のメッセージリスト。
    """
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
    """
    アシスタントからのメッセージを変換し、テキストと画像の情報を含む辞書に整理します。

    Parameters:
    messages (Messages): スレッド内のメッセージリスト。

    Returns:
    list: 変換されたメッセージのリスト。
    """
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
                file_paths = []
                if hasattr(content.text, "annotations"):
                    file_paths = [
                        {
                            "file_id": annotation.file_path.file_id,
                            "ext": os.path.splitext(annotation.text)[1][1:],  # 拡張子を抽出
                        }
                        for annotation in content.text.annotations
                        if annotation.__class__.__name__ == "TextAnnotationFilePath"
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
