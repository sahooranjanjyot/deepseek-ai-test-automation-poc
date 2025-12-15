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
            {"role": "system", "content": "Output ONLY valid Java code. No markdown fences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1400
    }
    r = requests.post(VLLM_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

with open("testcases/cancel_order.json") as f:
    test_case = json.load(f)

prompt = f"""
Generate Java Cucumber Step Definitions.

Rules:
- Output ONLY Java code (no markdown)
- package steps;
- class CancelOrderSteps
- Use @Given/@When/@Then
- Stub methods with TODO

Test Case JSON:
{json.dumps(test_case, indent=2)}
"""

java_code = strip_markdown_fences(ask_llm(prompt))

out_dir = Path("generated/steps")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "CancelOrderSteps.java"
out_file.write_text(java_code, encoding="utf-8")

print("✅ Steps generated at:", out_file)
