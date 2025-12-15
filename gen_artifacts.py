import json
import requests
from pathlib import Path

VLLM_URL = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/workspace/models/deepseek-coder-v2-lite"

def ask_llm(prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a test automation generator. Output only valid Gherkin, Java, or plain text. No markdown."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1200
    }
    response = requests.post(VLLM_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Load structured test case
with open("testcases/cancel_order.json") as f:
    test_case = json.load(f)

# Prepare output folders
Path("generated/features").mkdir(parents=True, exist_ok=True)

# Prompt for Gherkin
gherkin_prompt = f"""
Convert the following JSON test case into ONE Gherkin scenario.
Include clear navigation steps (menu clicks, page names).
Do not add explanations.

JSON:
{json.dumps(test_case, indent=2)}
"""

gherkin = ask_llm(gherkin_prompt)

Path("generated/features/cancel_order.feature").write_text(gherkin)

print("✅ Gherkin generated at generated/features/cancel_order.feature")
