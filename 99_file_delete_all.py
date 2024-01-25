from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

files = client.files.list()

for file in files:
    client.files.delete(file_id=file.id)

print("all files deleted")
