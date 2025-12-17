import hashlib
import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

# =========================
# Production Constants
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


# =========================
# RAG (fail-open)
# =========================
try:
    from rag_context_provider import get_llm_context  # type: ignore
    RAG_AVAILABLE = True
except ImportError:
    def get_llm_context(question: str, k: int = 3) -> str:
        return ""
    RAG_AVAILABLE = False


# =========================
# Env loading (force)
# =========================
def _load_env_local_force(repo_root: Path) -> None:
    """
    Loads KEY=VALUE lines from .env.local into os.environ.
    Unlike the helper you showed, this FORCE overrides keys (fixes stale env issues).
    """
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
    """
    1) Try your existing loader (if present)
    2) Force override from .env.local (so you never get stuck with wrong keys)
    """
    try:
        from tools.llm.env_loader import load_env_local  # type: ignore
        load_env_local(REPO_ROOT)
    except Exception:
        pass

    # FORCE override (this is what fixes your "403 Forbidden" loop)
    _load_env_local_force(REPO_ROOT)

    # Backward compatibility: if only OPENAI_API_KEY/DEEPSEEK_API_KEY is set,
    # also populate LOCAL_LLM_API_KEY to the same value if missing.
    if not os.getenv("LOCAL_LLM_API_KEY"):
        if os.getenv("OPENAI_API_KEY"):
            os.environ["LOCAL_LLM_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        elif os.getenv("DEEPSEEK_API_KEY"):
            os.environ["LOCAL_LLM_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")


# =========================
# Hash helpers
# =========================
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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

    return "\n".join([
        feature,
        "",
        scenario,
        f"  {given}",
        f"  {when}",
        f"  {then}",
    ])


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


# =========================
# Drift Detection (rag_docs)
# =========================
def compute_rag_docs_fingerprint() -> str:
    if not RAG_DOCS_DIR.exists():
        return "MISSING_RAG_DOCS"

    files = sorted(
        p for p in RAG_DOCS_DIR.glob("*.*")
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    )

    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def load_last_meta() -> dict:
    if META_PATH.exists():
        try:
            return json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def write_meta(meta: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def maybe_warn_or_rebuild_rag(docs_fingerprint: str) -> None:
    prev = load_last_meta()
    prev_fp = prev.get("rag_docs_fingerprint")

    if prev_fp and prev_fp != docs_fingerprint:
        print("DRIFT_DETECTED: rag_docs changed since last run.")
        print("PREV_FP:", prev_fp)
        print("CURR_FP:", docs_fingerprint)

        auto = os.getenv("RAG_AUTO_REBUILD", "0") == "1"
        if auto:
            print("RAG_AUTO_REBUILD=1 -> rebuilding index via rag_build.py")
            if not RAG_BUILD_SCRIPT.exists():
                print("WARN: rag_build.py missing, cannot rebuild automatically.")
                return
            r = subprocess.run([sys.executable, str(RAG_BUILD_SCRIPT)], capture_output=True, text=True)
            print(r.stdout)
            if r.returncode != 0:
                print(r.stderr)
                print("WARN: RAG rebuild failed; continuing fail-open.")
        else:
            print("WARN: Rebuild recommended: python rag_build.py")


# =========================
# LLM call
# =========================
def call_llm(prompt: str, task: str) -> str:
    from tools.llm.env_loader import load_env_local
    from tools.llm.local_client import local_chat

    load_env_local(REPO_ROOT)
    return local_chat(prompt, REPO_ROOT)   # <-- no model kwarg


# =========================
# Main
# =========================
def extract_strict_5_lines(raw: str) -> str:
    """
    Returns EXACTLY:
      Feature:
      Scenario:
      Given ...
      When ...
      Then ...
    from the raw LLM output (first occurrence only).
    Drops everything else (including extra scenarios and And/But).
    """
    lines = [l.rstrip() for l in raw.splitlines()]
    feature = None
    scenario = None
    given = None
    when = None
    then = None

    for l in lines:
        s = l.strip()
        if not s:
            continue

        if feature is None and s.startswith("Feature:"):
            feature = s
            continue

        # only take the first scenario AFTER we have feature
        if feature is not None and scenario is None and s.startswith("Scenario:"):
            scenario = s
            continue

        # Only capture steps after we have scenario
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

        # Ignore And/But and any other text by design

        if feature and scenario and given and when and then:
            break

    # If anything is missing, return raw so validator fails loudly
    if not (feature and scenario and given and when and then):
        return raw

    return "\n".join([feature, scenario, given, when, then])

if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        usage_exit()

    task = sys.argv[1].strip()

    ensure_env()

    contracts = load_contracts()
    contract_checksum = sha256(contracts)

    docs_fingerprint = compute_rag_docs_fingerprint()
    maybe_warn_or_rebuild_rag(docs_fingerprint)

    rag_context = get_llm_context(task, k=3) if RAG_AVAILABLE else ""
    rag_context = (rag_context or "").strip()
    rag_context_hash = sha256(rag_context) if rag_context else "EMPTY"

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
- Do NOT output headings, explanations, code fences, bullet points, or extra whitespace lines.
- Use plain text only.

CONTRACTS (REFERENCE ONLY):
{contracts}

RAG CONTEXT (OPTIONAL, MAY BE EMPTY):
{rag_context}

TASK:
{task}

REMINDER:
Return ONLY the 5 lines, nothing else.
""".strip()

    llm_output = call_llm(prompt, task)
    llm_output = extract_strict_5_lines(llm_output)
    print("=== RAW LLM OUTPUT START ===")
    print(llm_output)
    print("=== RAW LLM OUTPUT END ===")

    validate_llm_output(llm_output)
    normalized = normalize_output(llm_output)

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
        "rag_available": RAG_AVAILABLE,
        "rag_context_len": len(rag_context),
        "rag_context_hash": rag_context_hash,
        "rag_docs_fingerprint": docs_fingerprint,
        "local_llm_base_url": os.getenv("LOCAL_LLM_BASE_URL", ""),
        "local_llm_model": os.getenv("LOCAL_LLM_MODEL", DEFAULT_MODEL),
    }
    write_meta(meta)

    print("PROMPT_VERSION:", PROMPT_VERSION)
    print("CONTRACT_CHECKSUM:", contract_checksum)
    print("RAG_AVAILABLE:", RAG_AVAILABLE)
    print("RAG_CONTEXT_LEN:", len(rag_context))
    print("RAG_CONTEXT_HASH:", rag_context_hash)
    print("RAG_DOCS_FINGERPRINT:", docs_fingerprint)
    print("TASK:", task)
    print("FEATURE_NAME:", feature_name)
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