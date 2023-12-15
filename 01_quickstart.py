from openai import OpenAI

# OpenAIクライアントを初期化します。
client = OpenAI()

# チャットの補完を作成するためのリクエストを送信します。
# ここでは、モデル 'gpt-3.5-turbo' を使用しています。
completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        # システムロールのメッセージを設定します。これは、スパイダーマンのキャラクターを設定する指示です。
        {
            "role": "system",
            "content": "あなたは親愛なる隣人スパイダーマンです。話しかけたら小粋な受け答えをしてください。日本語で回答してください。",
        },
        # ユーザーロールのメッセージを設定します。これは、スパイダーマンに対する挨拶と質問です。
        {"role": "user", "content": "こんにちは！スパイダーマン！今日の調子はどうだい？"},
    ],
)

# 補完結果を出力します。これはスパイダーマンからの応答メッセージです。
print(completion.choices[0].message)
