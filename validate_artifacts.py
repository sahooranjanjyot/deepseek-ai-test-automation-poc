import os
import sys
import re

FEATURE_DIR = "generated/features"
STEPS_FILE = "generated/steps/CancelOrderSteps.java"
PAGES_DIR = "generated/pages"

def fail(msg):
    print(f"VALIDATION FAILED: {msg}")
    sys.exit(1)

def validate_feature_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip() for l in f.readlines()]

    # No markdown fences
    for l in lines:
        if "```" in l:
            fail(f"Markdown fence found in {path}")

    # Must start with Feature:
    non_empty = [l for l in lines if l.strip()]
    if not non_empty or not non_empty[0].startswith("Feature:"):
        fail(f"{path} must start with 'Feature:'")

    # Enforce exactly 1 Given / When / Then
    scenario_blocks = []
    current = []

    for line in lines:
        if line.strip().startswith(("Scenario:", "Scenario Outline:")):
            if current:
                scenario_blocks.append(current)
            current = [line]
        elif current:
            current.append(line)

    if current:
        scenario_blocks.append(current)

    for block in scenario_blocks:
        given = when = then = 0

        for line in block:
            s = line.strip()
            if s.startswith("Given "):
                given += 1
            elif s.startswith("When "):
                when += 1
            elif s.startswith("Then "):
                then += 1
            elif s.startswith(("And ", "But ")):
                fail(f"{path}: And/But not allowed")

        if given != 1 or when != 1 or then != 1:
            fail(
                f"{path}: Each scenario must have exactly "
                f"1 Given, 1 When, 1 Then"
            )

def validate_step_definitions():
    if not os.path.exists(STEPS_FILE):
        fail(f"Missing step definition file: {STEPS_FILE}")

    with open(STEPS_FILE, "r", encoding="utf-8") as f:
        src = f.read()

    given = src.count("@Given(")
    when = src.count("@When(")
    then = src.count("@Then(")

    if given != 1 or when != 1 or then != 1:
        fail(
            f"{STEPS_FILE}: Must contain exactly 1 @Given, 1 @When, 1 @Then. "
            f"Found Given={given}, When={when}, Then={then}"
        )

def validate_pages_atomic():
    if not os.path.isdir(PAGES_DIR):
        fail(f"Missing directory: {PAGES_DIR}")

    allowed_prefixes = (
        "click", "select", "enter", "type", "set", "fill",
        "open", "navigate", "goTo", "wait",
        "get", "is", "has",
        "verify", "assert"
    )

    forbidden_tokens = (
        "io.cucumber",
        "@Given", "@When", "@Then",
        "import io.cucumber"
    )

    method_re = re.compile(r"public\s+[\w\<\>\[\]]+\s+([A-Za-z_]\w*)\s*\(")

    for root, _, files in os.walk(PAGES_DIR):
        for file in files:
            if not file.endswith(".java"):
                continue

            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()

            for tok in forbidden_tokens:
                if tok in src:
                    fail(f"{path}: Page Objects must not contain Cucumber annotations")

            for m in method_re.finditer(src):
                name = m.group(1)
                if not name.startswith(allowed_prefixes):
                    fail(
                        f"{path}: Non-atomic public method '{name}'. "
                        f"Allowed prefixes: {', '.join(allowed_prefixes)}"
                    )

def main():
    if not os.path.isdir(FEATURE_DIR):
        fail(f"Missing directory: {FEATURE_DIR}")

    for root, _, files in os.walk(FEATURE_DIR):
        for file in files:
            if file.endswith(".feature"):
                validate_feature_file(os.path.join(root, file))

    validate_step_definitions()
    validate_pages_atomic()

    print("VALIDATION PASSED")

if __name__ == "__main__":
    main()
