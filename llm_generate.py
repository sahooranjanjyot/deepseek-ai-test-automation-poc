import hashlib
import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from rag.retrieve import retrieve  # your FAISS retriever
from tools.llm.local_client import chat_completion, list_models


# =========================
# Constants
# =========================
PROMPT_VERSION = "v1.0.0"

REPO_ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = REPO_ROOT / "contracts" / "ai_test_contracts.md"

GENERATED_DIR = REPO_ROOT / "generated"
GENERATED_FEATURES_DIR = GENERATED_DIR / "features"
GENERATED_STEPS_DIR = GENERATED_DIR / "steps"
GENERATED_PAGES_DIR = GENERATED_DIR / "pages"
META_PATH = GENERATED_DIR / "_meta.json"

RAG_DOCS_DIR = REPO_ROOT / "rag_docs"
RAG_BUILD_SCRIPT = REPO_ROOT / "rag_build.py"

DEFAULT_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
RAG_TOP_K = 3


# =========================
# Env loading (force override)
# =========================
def _load_env_local_force(repo_root: Path) -> None:
    env_path = repo_root / ".env.local"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            os.environ[k] = v


def ensure_env() -> None:
    # Load your existing helper if present, then FORCE override from .env.local
    try:
        from tools.llm.env_loader import load_env_local  # type: ignore
        load_env_local(REPO_ROOT)
    except Exception:
        pass
    _load_env_local_force(REPO_ROOT)

    # backward compat
    if not os.getenv("LOCAL_LLM_API_KEY"):
        if os.getenv("OPENAI_API_KEY"):
            os.environ["LOCAL_LLM_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        elif os.getenv("DEEPSEEK_API_KEY"):
            os.environ["LOCAL_LLM_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")

    if not os.getenv("LOCAL_LLM_MODEL"):
        os.environ["LOCAL_LLM_MODEL"] = DEFAULT_MODEL


# =========================
# Hash helpers
# =========================
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# =========================
# Core helpers
# =========================
def load_contracts() -> str:
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found: {CONTRACT_PATH}")
    return CONTRACT_PATH.read_text(encoding="utf-8")


def usage_exit() -> None:
    print('Usage: python llm_generate.py "Generate <feature name / story>"')
    sys.exit(2)


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "feature"


def to_pascal_case(text: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", text.strip())
    parts = [p for p in parts if p]
    if not parts:
        return "Feature"
    out = "".join(p[:1].upper() + p[1:] for p in parts)
    if out[0].isdigit():
        out = "F" + out
    return out


def extract_feature_name(gherkin_text: str) -> str:
    for line in gherkin_text.splitlines():
        line = line.strip()
        if line.startswith("Feature:"):
            return line[len("Feature:"):].strip() or "feature"
    return "feature"


# =========================
# Safety Guards
# =========================
def validate_llm_output(text: str) -> None:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if sum(l.startswith("Given ") for l in lines) != 1:
        raise ValueError("Must have exactly one Given")
    if sum(l.startswith("When ") for l in lines) != 1:
        raise ValueError("Must have exactly one When")
    if sum(l.startswith("Then ") for l in lines) != 1:
        raise ValueError("Must have exactly one Then")

    for l in lines:
        if l.startswith("And ") or l.startswith("But "):
            raise ValueError("And/But not allowed")

    if not any(l.startswith("Feature:") for l in lines):
        raise ValueError("Missing Feature")
    if not any(l.startswith("Scenario:") for l in lines):
        raise ValueError("Missing Scenario")


def normalize_output(text: str) -> str:
    raw = [l.strip() for l in text.splitlines() if l.strip()]

    feature = next(l for l in raw if l.startswith("Feature:"))
    scenario = next(l for l in raw if l.startswith("Scenario:"))
    given = next(l for l in raw if l.startswith("Given "))
    when = next(l for l in raw if l.startswith("When "))
    then = next(l for l in raw if l.startswith("Then "))

    return "\n".join([feature, "", scenario, f"  {given}", f"  {when}", f"  {then}"])


def extract_strict_5_lines(raw: str) -> str:
    """
    Returns EXACTLY:
      Feature:
      Scenario:
      Given ...
      When ...
      Then ...
    from the raw LLM output (first occurrence only).
    """
    lines = [l.rstrip() for l in raw.splitlines()]
    feature = scenario = given = when = then = None

    for l in lines:
        s = l.strip()
        if not s:
            continue

        if feature is None and s.startswith("Feature:"):
            feature = s
            continue

        if feature is not None and scenario is None and s.startswith("Scenario:"):
            scenario = s
            continue

        if scenario is not None:
            if given is None and s.startswith("Given "):
                given = s
                continue
            if when is None and s.startswith("When "):
                when = s
                continue
            if then is None and s.startswith("Then "):
                then = s
                continue

        if feature and scenario and given and when and then:
            break

    if not (feature and scenario and given and when and then):
        return raw

    return "\n".join([feature, scenario, given, when, then])


# =========================
# Writers
# =========================
def ensure_dirs() -> None:
    GENERATED_FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_STEPS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_PAGES_DIR.mkdir(parents=True, exist_ok=True)


def write_feature(content: str, feature_name: str) -> Path:
    ensure_dirs()
    filename = f"{slugify(feature_name)}.feature"
    path = GENERATED_FEATURES_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def write_page_object(class_base: str) -> Path:
    ensure_dirs()
    page_class = f"{class_base}Page"
    path = GENERATED_PAGES_DIR / f"{page_class}.java"
    code = f"""\
package generated.pages;

public class {page_class} {{

    public void openStartPage() {{
        // atomic navigation action
    }}

    public void clickMainAction() {{
        // atomic click action
    }}

    public void verifyExpectedResultIsShown() {{
        // atomic verification
    }}

    private void waitForReady() {{
        // helper
    }}
}}
"""
    path.write_text(code, encoding="utf-8")
    return path


def write_steps(class_base: str) -> Path:
    ensure_dirs()
    steps_class = f"{class_base}Steps"
    page_class = f"{class_base}Page"
    path = GENERATED_STEPS_DIR / f"{steps_class}.java"
    code = f"""\
package generated.steps;

import generated.pages.{page_class};
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

public class {steps_class} {{

    private final {page_class} page = new {page_class}();

    @Given("user is on the start page")
    public void userIsOnTheStartPage() {{
        page.openStartPage();
    }}

    @When("user performs the main action")
    public void userPerformsTheMainAction() {{
        page.clickMainAction();
    }}

    @Then("expected result is shown")
    public void expectedResultIsShown() {{
        page.verifyExpectedResultIsShown();
    }}
}}
"""
    path.write_text(code, encoding="utf-8")
    return path


def write_meta(meta: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


# =========================
# Main
# =========================
if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        usage_exit()

    task = sys.argv[1].strip()

    ensure_env()

    # quick readiness check (this will fail loudly if Cloudflare blocks)
    try:
        _ = list_models()
        print("LOCAL_LLM_READY: /v1/models OK")
    except Exception as e:
        print("LOCAL_LLM_NOT_READY")
        raise

    # RAG retrieve
    rag_results = retrieve(task, top_k=RAG_TOP_K)
    rag_context = "\n".join([f"[{r['doc']}#{r['chunk']}] {r.get('content','')}" for r in rag_results]).strip()
    rag_available = bool(rag_context)
    rag_context_hash = sha256(rag_context) if rag_available else "EMPTY"

    contracts = load_contracts()
    contract_checksum = sha256(contracts)

    prompt = f"""
SYSTEM:
You are a STRICT Gherkin test automation generator.

OUTPUT FORMAT (MUST FOLLOW EXACTLY):
- Return EXACTLY 5 non-empty lines.
- Line 1 must start with: Feature:
- Line 2 must start with: Scenario:
- Line 3 must start with: Given
- Line 4 must start with: When
- Line 5 must start with: Then
- Do NOT output any other lines.
- Do NOT output "And" or "But".
- Do NOT output multiple scenarios.
- Use plain text only.

CONTRACTS (REFERENCE ONLY):
{contracts}

RAG CONTEXT (OPTIONAL):
{rag_context}

TASK:
{task}

REMINDER:
Return ONLY the 5 lines, nothing else.
""".strip()

    raw = chat_completion(prompt)
    raw = extract_strict_5_lines(raw)

    print("=== RAW LLM OUTPUT START ===")
    print(raw)
    print("=== RAW LLM OUTPUT END ===")

    validate_llm_output(raw)
    normalized = normalize_output(raw)

    feature_name = extract_feature_name(normalized) or task
    class_base = to_pascal_case(feature_name)

    feature_path = write_feature(normalized, feature_name)
    page_path = write_page_object(class_base)
    steps_path = write_steps(class_base)

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "task": task,
        "feature_name": feature_name,
        "feature_file": str(feature_path),
        "page_file": str(page_path),
        "steps_file": str(steps_path),
        "contract_checksum": contract_checksum,
        "rag": {
            "enabled": True,
            "top_k": RAG_TOP_K,
            "available": rag_available,
            "context_len": len(rag_context),
            "context_hash": rag_context_hash,
            "docs": [f"{r['doc']}#{r['chunk']}" for r in rag_results],
        },
        "local_llm_base_url": os.getenv("LOCAL_LLM_BASE_URL", ""),
        "local_llm_model": os.getenv("LOCAL_LLM_MODEL", DEFAULT_MODEL),
    }
    write_meta(meta)

    print("PROMPT_VERSION:", PROMPT_VERSION)
    print("CONTRACT_CHECKSUM:", contract_checksum)
    print("RAG_AVAILABLE:", rag_available)
    print("RAG_CONTEXT_LEN:", len(rag_context))
    print("RAG_CONTEXT_HASH:", rag_context_hash)
    print("RAG_TOPK_DOCS:", [f"{r['doc']}#{r['chunk']}" for r in rag_results])
    print("FEATURE_WRITTEN:", feature_path)
    print("PAGE_WRITTEN:", page_path)
    print("STEPS_WRITTEN:", steps_path)
    print("META_WRITTEN:", META_PATH)

    print("RUNNING validate_artifacts.py")
    result = subprocess.run([sys.executable, "validate_artifacts.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)