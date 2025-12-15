import json
import requests
from pathlib import Path
from rag_injector import build_prompt

VLLM_URL = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/workspace/models/deepseek-coder-v2-lite"

def ask_llm(prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Generate ONLY valid Java code. No markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1200
    }
    r = requests.post(VLLM_URL, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

with open("testcases/cancel_order.json") as f:
    test_case = json.load(f)

task = f"""
Generate Java Cucumber Step Definitions.

Rules:
- Use @Given, @When, @Then
- No implementation logic, only method stubs
- Class name: CancelOrderSteps
- Package: steps

Test Case JSON:
{json.dumps(test_case, indent=2)}
"""

# 🔥 THIS IS RAG INJECTON
prompt = build_prompt(task)

java_code = ask_llm(prompt)

out_dir = Path("generated/steps")
out_dir.mkdir(parents=True, exist_ok=True)

out_file = out_dir / "CancelOrderSteps.java"
out_file.write_text(java_code)

print("✅ Steps generated with RAG grounding:", out_file)
