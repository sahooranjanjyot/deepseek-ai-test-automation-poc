import json
import requests
from rag_retrieve import get_context

VLLM_URL = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/workspace/models/deepseek-coder-v2-lite"

# This is the USER QUERY (not hardcoded output)
USER_QUERY = "How should order cancellation and payment handling be validated?"

# Step 1: Retrieve relevant context
context = get_context(USER_QUERY)

# Step 2: Ask LLM using retrieved context
prompt = f"""
You are a senior test automation architect.

Use ONLY the SYSTEM CONTEXT below to answer.
If information is missing, say so explicitly.

SYSTEM CONTEXT:
{context}

QUESTION:
{USER_QUERY}
"""

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Answer concisely and accurately."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.1,
    "max_tokens": 400
}

response = requests.post(VLLM_URL, json=payload)
response.raise_for_status()

answer = response.json()["choices"][0]["message"]["content"]

print("===== LLM ANSWER =====")
print(answer)
print("======================")
