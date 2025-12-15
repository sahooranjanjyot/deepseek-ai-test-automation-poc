import json
import requests
from pathlib import Path
from sanitize import strip_markdown_fences

VLLM_URL = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/workspace/models/deepseek-coder-v2-lite"

def ask_llm(prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Output ONLY valid Gherkin. No markdown fences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1200
    }
    r = requests.post(VLLM_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

with open("testcases/cancel_order.json") as f:
    test_case = json.load(f)

Path("generated/features").mkdir(parents=True, exist_ok=True)

prompt = f"""
Generate a complete Gherkin feature file for this test case.
Rules:
- MUST start with a line: Feature: <something>
- Include exactly one Scenario
- Include at least one Then step
- No markdown fences

Test case JSON:
{json.dumps(test_case, indent=2)}
"""

gherkin = strip_markdown_fences(ask_llm(prompt))

# Enforce Feature: header if model forgets
if not gherkin.lstrip().startswith("Feature:"):
    gherkin = "Feature: Order Cancellation\n\n" + gherkin

Path("generated/features/cancel_order.feature").write_text(gherkin, encoding="utf-8")
print("✅ Gherkin generated at generated/features/cancel_order.feature")
