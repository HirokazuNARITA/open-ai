from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
client = OpenAI()

vs_list = client.beta.vector_stores.list()
for vs in vs_list:
    client.beta.vector_stores.delete(vector_store_id=vs.id)

print("vector store deleted")
