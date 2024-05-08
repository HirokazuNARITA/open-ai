import os
from openai import OpenAI
from openai.types.beta.threads import (
    ImageFile,
    Text,
    TextContentBlock,
    ImageFileContentBlock,
)
import backoff
import requests
from typing_extensions import override
from openai import AssistantEventHandler
from typing import List


class StreamingEventHandler(AssistantEventHandler):
    def __init__(self, assistant_pronpt="assistant >"):
        super().__init__()  # 基底クラスのコンストラクタを呼び出す
        self.file_ids: List[str] = []  # ファイルIDを保持するためのリスト
        self.assistant_prompt = assistant_pronpt

    @override
    def on_text_created(self, text) -> None:
        """
        OpenAISDKでテキストがStreamingにより作成されたときに呼び出されるイベントハンドラーです。

        Parameters:
        text (str): 作成されたテキスト。
        """
        print(f"{self.assistant_prompt}", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        """
        テキストに変更があったときに呼び出されるイベントハンドラーです。

        Parameters:
        delta (Delta): テキストの変更内容を含むデルタオブジェクト。
        snapshot: 変更後のテキストのスナップショット。
        """
        print(delta.value, end="", flush=True)

    @override
    def on_text_done(self, text: Text) -> None:
        """テキストの出力が終了したときに呼び出されるイベントハンドラーです。

        Parameters:
        text (str): 作成されたテキスト。
        """
        print("", end="\n")

    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        print("on_message_done.....")
        print(message)

        for m_content in message.content:
            if isinstance(m_content, TextContentBlock):
                message_content = message.content[0].text  # type: ignore
                annotations = message_content.annotations
                citations = []
                for index, annotation in enumerate(annotations):
                    message_content.value = message_content.value.replace(
                        annotation.text, f"[{index}]"
                    )
                    if file_citation := getattr(annotation, "file_citation", None):
                        # cited_file = client.files.retrieve(file_citation.file_id)
                        # citations.append(f"[{index}] {cited_file.filename}")
                        print(file_citation)
                        self.file_ids.append(file_citation.file_id)
            elif isinstance(m_content, ImageFileContentBlock):
                # MessageContentImageFile の場合
                self.file_ids.append(m_content.image_file.file_id)

    def on_tool_call_created(self, tool_call):
        """
        ツールの呼び出しが作成されたときに呼び出されるイベントハンドラーです。

        Parameters:
        tool_call (ToolCall): 作成されたツールの呼び出しオブジェクト。
        """
        print(f"{self.assistant_prompt} {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        """
        ツールの呼び出しに変更があったときに呼び出されるイベントハンドラーです。

        Parameters:
        delta (Delta): ツールの呼び出しの変更内容を含むデルタオブジェクト。
        snapshot: 変更後のツールの呼び出しのスナップショット。
        """
        if delta.type == "code_interpreter":
            if delta.code_interpreter.input:  # type: ignore
                print(delta.code_interpreter.input, end="", flush=True)  # type: ignore
            if delta.code_interpreter.outputs:  # type: ignore
                print(delta)
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:  # type: ignore
                    print("--output information--")
                    print(f"\n{output}")  # type: ignore
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)
                    elif output.type == "image":
                        self.file_ids.append(output.image.file_id)  # type: ignore


def file_download(file_id, file_path):
    client = OpenAI()
    data = client.files.content(file_id=file_id)
    data_bytes = data.read()

    directory = os.path.dirname(file_path)
    # ディレクトリが存在しない場合は作成
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    # ファイルをオープン
    with open(file_path, "wb") as file:
        file.write(data_bytes)


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
            # print(content.__class__.__name__)
            if isinstance(content, TextContentBlock):
                # MessageContentText の場合
                text_info = content.text.value
                file_paths = []
                if hasattr(content.text, "annotations"):
                    file_paths = [
                        {
                            "file_id": annotation.file_path.file_id,  # type: ignore
                            "ext": os.path.splitext(annotation.text)[1][
                                1:
                            ],  # 拡張子を抽出
                        }
                        for annotation in content.text.annotations
                        if annotation.__class__.__name__ == "TextAnnotationFilePath"
                    ]
                text_content = {
                    "type": "text",
                    "value": text_info,
                    "file_ids": file_paths,
                }
            elif isinstance(content, ImageFileContentBlock):
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
