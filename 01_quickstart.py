from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
  model='gpt-3.5-turbo',
  messages=[
    {"role": "system", "content": "あなたは親愛なる隣人スパイダーマンです。話しかけたら小粋な受け答えをしてください。日本語で回答してください。"},
    {"role": "user", "content": "こんにちは！スパイダーマン！今日の調子はどうだい？"}
  ]
)

print(completion.choices[0].message)