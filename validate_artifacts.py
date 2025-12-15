import os
import sys

FEATURE_DIR = "generated/features"

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

    # Enforce 1 Given, 1 When, 1 Then per scenario
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

def main():
    for root, _, files in os.walk(FEATURE_DIR):
        for file in files:
            if file.endswith(".feature"):
                validate_feature_file(os.path.join(root, file))

    print("VALIDATION PASSED")

if __name__ == "__main__":
    main()
