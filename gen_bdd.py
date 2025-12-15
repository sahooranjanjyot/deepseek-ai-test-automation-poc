import json, re
from pathlib import Path
import urllib.request

API = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/workspace/models/deepseek-coder-v2-lite"

JIRA_STORY = """
User Story:
As a customer, I want to cancel an order and validate that I am not charged for that.

Acceptance Criteria:
1) If the order is in a cancellable state (Pending/Processing), user can cancel successfully.
2) After cancellation, the order status shows Cancelled.
3) Payment is not captured/charged after cancellation.
4) If payment was authorized, it should be voided/released.
5) If the order is not cancellable (Shipped/Delivered), cancellation is blocked with a clear message.
6) Cancellation is reflected in Order History.
"""

PROMPT = f"""
Generate TWO outputs: (A) a Gherkin feature file and (B) Java step definition skeleton.

Constraints:
- Use Gherkin with Feature/Background and Scenario Outline where appropriate.
- Include scenarios for:
  - cancellable order
  - non-cancellable order
  - payment authorized but not captured
  - payment already captured (mark refund check as TODO)
- Steps must be automatable with Selenium.
- Output must be STRICT JSON with exactly these keys:
  feature_file_name, feature_file_content, step_file_name, step_file_content
- Java steps must be Cucumber-Java with @Given/@When/@Then and TODO bodies.
- Do NOT include markdown fences.

Jira Story:
{JIRA_STORY}
"""

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Return STRICT JSON only. No markdown. No commentary."},
        {"role": "user", "content": PROMPT}
    ],
    "temperature": 0.2,
    "max_tokens": 1800
}

req = urllib.request.Request(
    API,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req, timeout=300) as r:
    data = json.loads(r.read().decode("utf-8"))

txt = data["choices"][0]["message"]["content"].strip()

# Defensive cleanup
txt = re.sub(r"^\s*```(?:json)?\s*\n?", "", txt, flags=re.I)
txt = re.sub(r"\n?\s*```\s*$", "", txt)

obj = json.loads(txt)

base = Path("/workspace/selenium-poc/generated_bdd")
base.mkdir(parents=True, exist_ok=True)

feature_path = base / obj["feature_file_name"]
step_path = base / obj["step_file_name"]

feature_path.write_text(obj["feature_file_content"].strip() + "\n", encoding="utf-8")
step_path.write_text(obj["step_file_content"].strip() + "\n", encoding="utf-8")

print("[OK] Generated:")
print(" -", feature_path)
print(" -", step_path)
