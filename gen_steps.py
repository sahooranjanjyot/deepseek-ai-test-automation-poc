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
            {
                "role": "system",
                "content": "Output ONLY valid Java code. No markdown. No explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1600
    }

    r = requests.post(VLLM_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

with open("testcases/cancel_order.json") as f:
    test_case = json.load(f)

prompt = f"""
Generate Java Cucumber Step Definitions.

STRICT REQUIREMENTS (DO NOT VIOLATE):
1) Generate EXACTLY THREE step definition methods:
   - one @Given
   - one @When
   - one @Then
2) Do NOT generate And / But steps.
3) Do NOT generate additional Given/When/Then methods.
4) Each of the three step methods MUST orchestrate multiple granular actions.
5) Granular actions MUST be implemented as private helper methods in the SAME class.
6) Helper methods must contain TODO comments only.
7) Package name MUST be: steps
8) Class name MUST be: CancelOrderSteps
9) Output MUST be pure Java code only.

Business intent:
- Given = user logged in with a paid/cancellable order
- When = user cancels the order from order history
- Then = order is cancelled and confirmation is shown

Test case JSON:
{json.dumps(test_case, indent=2)}
"""

java_code = strip_markdown_fences(ask_llm(prompt))

out_dir = Path("generated/steps")
out_dir.mkdir(parents=True, exist_ok=True)

out_file = out_dir / "CancelOrderSteps.java"
out_file.write_text(java_code, encoding="utf-8")

print("✅ Steps generated at:", out_file)
