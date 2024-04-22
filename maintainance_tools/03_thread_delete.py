from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
client = OpenAI()

thead_ids = []

for id in thead_ids:
    client.beta.threads.delete(thread_id=id)

print("threads deleted")
