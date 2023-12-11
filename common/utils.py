from openai import OpenAI
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
)
import backoff
import requests


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=30)
def retreve_runs(client, thread_id, run_id):
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

    print("------runの回収中------")
    print(run)

    if run.status == "completed":
        print("Runが完了しました。")
        return run
    elif run.status == "failed":
        print("Runが失敗しました。")
        return run
    elif run.status == "expired":
        print("Runが期限切れになりました。")
        return run

    # まだ完了していない場合は例外を発生させてリトライ
    raise requests.exceptions.RequestException("Runはまだ完了していません。")


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
