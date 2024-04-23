from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI()

assistants = client.beta.assistants.list()
for assistant in assistants:
    client.beta.assistants.delete(assistant_id=assistant.id)

print("delete all assistants...")
