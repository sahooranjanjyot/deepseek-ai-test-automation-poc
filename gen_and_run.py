import json, re, subprocess, sys
from pathlib import Path
import urllib.request

API = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/workspace/models/deepseek-coder-v2-lite"

PROMPT = (
    "Generate a complete Java Selenium WebDriver JUnit5 test class named ExampleTest. "
    "It must open https://example.com, assert the title 'Example Domain', "
    "use WebDriverManager, run headless with ChromeOptions (binary /usr/bin/google-chrome), "
    "and quit the driver in @AfterEach. Output ONLY Java code. NO markdown fences."
)

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Return ONLY raw Java code. Do NOT use ``` fences. Do NOT add explanations."},
        {"role": "user", "content": PROMPT},
    ],
    "temperature": 0.2,
    "max_tokens": 1400,
}

req = urllib.request.Request(
    API,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req, timeout=600) as r:
    data = json.loads(r.read().decode("utf-8"))

code = data["choices"][0]["message"]["content"].strip()

# Strip markdown fences if present
code = re.sub(r"^\s*```(?:java)?\s*\n", "", code, flags=re.IGNORECASE)
code = re.sub(r"\n\s*```\s*$", "", code)

# Strip accidental leading label line like "java"
if code.lower().startswith("java\n"):
    code = code.split("\n", 1)[1].lstrip()

# Strip trailing stray dot
code = code.rstrip().rstrip(".")

test_path = Path("/workspace/selenium-poc/src/test/java/ExampleTest.java")
test_path.write_text(code + "\n", encoding="utf-8")
print(f"[OK] Wrote: {test_path} ({test_path.stat().st_size} bytes)")

cmd = ["mvn", "-q", "-Dtest=ExampleTest", "test"]
print("[RUN]", " ".join(cmd))
p = subprocess.run(cmd, cwd="/workspace/selenium-poc")
sys.exit(p.returncode)
