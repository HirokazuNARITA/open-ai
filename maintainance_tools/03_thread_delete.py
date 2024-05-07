from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
client = OpenAI()

thead_ids = []

for id in thead_ids:
    client.beta.threads.delete(thread_id=id)

print("threads deleted")


# OpenAIのプラットフォーム＞Thread画面でChromeのDeveloperツールのコンソールを起動して以下のコードを実行すると
# 画面上のthread_idを取得できる。
# const elements = Array.from(document.querySelectorAll('.thread-list-subheading-id'));
# const texts = elements.map(element => element.innerText);
# console.log(texts);
