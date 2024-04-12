from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

thead_ids = [
    "thread_SlLIeT0lfSmIOzk3CkSjJrwh",
    "thread_8pdZ8gxK1moQkfrgnyL8tr1K",
    "thread_Dd4Hpc2KsuQ1QWmTZF2BmseV",
    "thread_XXjWRh3P8jpsuzpEt7NcETpF",
    "thread_YpdkhiiSjAy5cRG3ti9AN3Ew",
    "thread_U3pokLrgEp37r6o9CoYnPrve",
    "thread_Be66TBcc0Fgcms0MUxiCJXUX",
    "thread_Sdg1hlwWI44OMfXXtopc3ELR",
    "thread_GvSTDijR6vSTcHpFnguEuZFj",
    "thread_wLqKhbu8WbT1H0gCr4KBT3D4",
    "thread_BCfDwXNRkux8GH8dzUSdNgTy",
    "thread_xmgKfTk4wS7S9cLSp7VnkcQu",
    "thread_RKzPNOVp0uMrcjt4DLvErE6c",
    "thread_12e0o62Ud8wA8t2zRjBCQ6ZE",
    "thread_qXiAoKTEBZyLRYbpdubNSv5T",
    "thread_wVnGptnbkOD1hF729znvOjjO",
    "thread_qSMUl7nk9qLClVU9hGFtEfKt",
    "thread_k7LKZNyHHmkeIEmhy61mjZdf",
]

for id in thead_ids:
    client.beta.threads.delete(thread_id=id)

print("threads deleted")
