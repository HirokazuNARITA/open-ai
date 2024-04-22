import requests
import json


def send_message_and_get_stream(message):
    url = "http://localhost:8000/assistant/queue"  # FastAPIサーバーのエンドポイント
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"message": message})

    with requests.post(url, headers=headers, data=data, stream=True) as response:
        buffer = b""  # バッファの初期化
        print("ボット: ", end="", flush=True)
        try:
            for byte in response.iter_content(chunk_size=1):
                buffer += byte
                try:
                    char = buffer.decode("utf-8")
                    print(char, end="", flush=True)
                    buffer = b""  # バッファをクリア
                except UnicodeDecodeError:
                    # マルチバイト文字の途中であれば、バッファに蓄積を続ける
                    continue
            print()  # レスポンスの後に改行を入れる
        except Exception as e:
            print(f"\nAn error occurred: {e}")


# 使用例
while True:
    input_msg = input("あなた: ")
    if input_msg == "さようなら":
        break
    send_message_and_get_stream(input_msg)
