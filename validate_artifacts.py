import json
import re
import sys
from pathlib import Path

FAILS = []

def fail(msg):
    FAILS.append(msg)

def must_exist(p: Path, label: str):
    if not p.exists():
        fail(f"Missing {label}: {p}")

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Invalid JSON in {p}: {e}")
        return None

def check_no_markdown_fences(text: str, label: str):
    if "```" in text:
        fail(f"{label} contains markdown fences (```), reject it.")

def check_testcase_schema(tc: dict):
    required = [
        "test_id",
        "title",
        "preconditions",
        "steps",
        "postconditions",
        "test_data",
        "automation_eligibility",
        "notes"
    ]

    for k in required:
        if k not in tc:
            fail(f"Testcase missing key: {k}")

    steps = tc.get("steps")

    if not isinstance(steps, list) or len(steps) == 0:
        fail("Testcase steps must be a non-empty list.")
        return

    expected_no = 1
    for s in steps:
        if s.get("step_no") != expected_no:
            fail(f"Step numbers not sequential. Expected {expected_no}, got {s.get('step_no')}.")
        expected_no += 1

        nav = s.get("navigation", {})
        for nk in ["from_page", "action", "ui_element"]:
            if nk not in nav or not str(nav.get(nk, "")).strip():
                fail(f"Step {s.get('step_no')} navigation missing/blank: {nk}")

        if not str(s.get("action", "")).strip():
            fail(f"Step {s.get('step_no')} action is blank")

        if not str(s.get("expected_result", "")).strip():
            fail(f"Step {s.get('step_no')} expected_result is blank")

def check_feature_basic(feature_text: str):
    check_no_markdown_fences(feature_text, "Gherkin feature")

    if "Feature:" not in feature_text:
        fail("Feature file missing 'Feature:' line.")

    if not re.search(r"^\s*Scenario", feature_text, flags=re.MULTILINE):
        fail("Feature file missing any Scenario.")

    if not re.search(r"^\s*Then\s+", feature_text, flags=re.MULTILINE):
        fail("Feature file missing a Then step (assertion).")

def check_java_basic(java_text: str, label: str):
    check_no_markdown_fences(java_text, label)

    if "package " not in java_text:
        fail(f"{label} missing package declaration.")

    if "class " not in java_text:
        fail(f"{label} missing class declaration.")

def check_steps_has_cucumber_annotations(java_text: str):
    if not any(a in java_text for a in ["@Given", "@When", "@Then"]):
        fail("Step definitions missing Cucumber annotations.")

def check_pages_present(pages_dir: Path):
    files = list(pages_dir.glob("*.java"))
    if not files:
        fail(f"No Page Objects found in {pages_dir}")
        return

    for f in files:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        check_java_basic(txt, f"Page Object {f.name}")

def main():
    tc_path = Path("testcases/cancel_order.json")
    feat_path = Path("generated/features/cancel_order.feature")
    steps_path = Path("generated/steps/CancelOrderSteps.java")
    pages_dir = Path("generated/pages")

    must_exist(tc_path, "test case JSON")
    must_exist(feat_path, "feature file")
    must_exist(steps_path, "step definitions")
    must_exist(pages_dir, "pages directory")

    if tc_path.exists():
        tc = load_json(tc_path)
        if tc:
            check_testcase_schema(tc)

    if feat_path.exists():
        check_feature_basic(feat_path.read_text(encoding="utf-8", errors="ignore"))

    if steps_path.exists():
        steps_text = steps_path.read_text(encoding="utf-8", errors="ignore")
        check_java_basic(steps_text, "Step definitions")
        check_steps_has_cucumber_annotations(steps_text)

    if pages_dir.exists():
        check_pages_present(pages_dir)

    if FAILS:
        print("❌ VALIDATION FAILED")
        for i, m in enumerate(FAILS, 1):
            print(f"{i}. {m}")
        sys.exit(2)

    print("✅ VALIDATION PASSED")

if __name__ == "__main__":
    main()
