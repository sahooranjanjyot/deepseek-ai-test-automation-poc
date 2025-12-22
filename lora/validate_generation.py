import json
import re
import sys
from pathlib import Path

REQUIRED_KEYS = {"feature_file", "step_definitions", "page_objects", "notes"}

def fail(msg):
    print("VALIDATION_FAILED:", msg)
    sys.exit(2)

def validate_feature(text: str):
    if "Feature:" not in text:
        fail("feature_file missing 'Feature:'")
    if "Scenario" not in text:
        fail("feature_file missing 'Scenario' or 'Scenario Outline'")
    bad_lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("Feature:", "Scenario", "Scenario Outline:", "Background:", "@")):
            continue
        if re.match(r"^(Given|When|Then|And|But)\b", s):
            continue
        if s.startswith("#"):
            continue
        bad_lines.append(s)
    if bad_lines:
        fail(f"feature_file contains non-Gherkin lines: {bad_lines[:3]}")

def validate_steps(step_obj: dict, feature_text: str):
    if "language" not in step_obj or "code" not in step_obj:
        fail("step_definitions must have {language, code}")
    code = step_obj["code"]
    if step_obj["language"].lower() != "java":
        fail("Only java is validated right now (set language=java)")
    if "@Given" not in code and "@When" not in code and "@Then" not in code:
        fail("Java step definitions missing @Given/@When/@Then annotations")

    steps = []
    for line in feature_text.splitlines():
        s = line.strip()
        m = re.match(r"^(Given|When|Then|And|But)\s+(.*)$", s)
        if m:
            steps.append(m.group(2))
    if not steps:
        fail("No steps extracted from feature_file")

    # lightweight check: ensure at least half steps have some corresponding annotation regex text in code
    hits = 0
    for st in steps:
        token = re.sub(r'["\']', "", st).split(" ")[0]
        if token and token in code:
            hits += 1
    if hits < max(1, len(steps)//2):
        fail("Step definitions don't appear to align with feature steps (low match score)")

def validate_pages(pages):
    if not isinstance(pages, list) or len(pages) == 0:
        fail("page_objects must be a non-empty list")
    for p in pages:
        if "name" not in p or "code" not in p:
            fail("Each page object must have {name, code}")
        if not p["name"].endswith(".java"):
            fail(f"page object name must end with .java: {p['name']}")
        if "class " not in p["code"]:
            fail(f"page object {p['name']} missing class declaration")
        if "By." not in p["code"] and "@FindBy" not in p["code"]:
            fail(f"page object {p['name']} missing locators (By.* or @FindBy)")

def main():
    if len(sys.argv) != 2:
        print("Usage: python lora/validate_generation.py <output.json>")
        sys.exit(1)

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        fail(f"Missing keys: {sorted(missing)}")

    validate_feature(data["feature_file"])
    validate_steps(data["step_definitions"], data["feature_file"])
    validate_pages(data["page_objects"])

    print("VALIDATION_PASSED")

if __name__ == "__main__":
    main()
