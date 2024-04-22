from openai import OpenAI

client = OpenAI()

assistants = client.beta.assistants.list()
for assistant in assistants:
    client.beta.assistants.delete(assistant_id=assistant.id)

print("delete all assistants...")
