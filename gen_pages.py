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

pages = [
    ("OrderHistoryPage", "Order History page listing orders and opening order details"),
    ("OrderDetailsPage", "Order Details page including Cancel Order action"),
    ("CancellationConfirmationDialog", "Confirmation dialog for order cancellation")
]

out_dir = Path("generated/pages")
out_dir.mkdir(parents=True, exist_ok=True)

for cls, desc in pages:
    prompt = f"""
Generate a Java Selenium Page Object.

Rules:
- Output ONLY Java code (no markdown)
- package pages;
- class {cls}
- Constructor(WebDriver driver)
- Use By locators as placeholders (TODO)
- Provide methods needed by the test case

Page purpose: {desc}

Test Case JSON:
{json.dumps(test_case, indent=2)}
"""
    code = strip_markdown_fences(ask_llm(prompt))
    out_file = out_dir / f"{cls}.java"
    out_file.write_text(code, encoding="utf-8")
    print("✅ Page generated:", out_file)
