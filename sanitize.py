import re

def strip_markdown_fences(text: str) -> str:
    if text is None:
        return ""
    t = text.strip()

    # Remove starting fence like ``` or ```java or ```gherkin
    t = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*\n?", "", t)

    # Remove ending fence
    t = re.sub(r"\n?\s*```\s*$", "", t)

    return t.strip() + "\n"
