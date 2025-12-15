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
                "content": (
                    "You are a senior Selenium automation architect. "
                    "Generate ONLY valid Java code. "
                    "No markdown. No explanations."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1400
    }
    r = requests.post(VLLM_URL, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# -------------------------------
# Load test case
# -------------------------------
with open("testcases/cancel_order.json") as f:
  test_case = json.load(f)

pages = [
    {
        "name": "OrderHistoryPage",
        "description": "Represents Order History page where user can view past orders"
    },
    {
        "name": "OrderDetailsPage",
        "description": "Represents Order Details page for a selected order"
    },
    {
        "name": "CancellationConfirmationDialog",
        "description": "Represents cancellation confirmation dialog"
    }
]

out_dir = Path("generated/pages")
out_dir.mkdir(parents=True, exist_ok=True)

for page in pages:
    prompt = f"""
Generate a Java Selenium Page Object.

Rules:
- Package: pages
- Class name: {page['name']}
- Use WebDriver
- Use By locators (placeholders allowed)
- Include constructor(WebDriver)
- Include methods based on test case actions
- Do NOT hardcode waits (use TODO comments)

Page description:
{page['description']}

Test Case Context:
{json.dumps(test_case, indent=2)}
"""

    java_code = ask_llm(prompt)
    out_file = out_dir / f"{page['name']}.java"
    out_file.write_text(java_code)
    print(f"✅ Generated {out_file}")

