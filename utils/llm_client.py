import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(prompt: str, system: str = "You are a helpful assistant.") -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ]
    )
    return response.choices[0].message.content