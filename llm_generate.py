import os
# Must be set before any HF tokenizers / sentence-transformers usage to avoid fork warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import hashlib
import json
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

from rag.retrieve import retrieve  # your FAISS retriever


# =========================
# Constants
# =========================
PROMPT_VERSION = "v1.1.1"

REPO_ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = REPO_ROOT / "contracts" / "ai_test_contracts.md"

GENERATED_DIR = REPO_ROOT / "generated"
GENERATED_FEATURES_DIR = GENERATED_DIR / "features"
GENERATED_STEPS_DIR = GENERATED_DIR / "steps"
GENERATED_PAGES_DIR = GENERATED_DIR / "pages"
META_PATH = GENERATED_DIR / "_meta.json"

DEFAULT_MODEL = "deepseek-v2-lite-lora-merged"
RAG_TOP_K = 3

# Keep in sync with validate_artifacts.py allowed prefixes
ALLOWED_METHOD_PREFIXES = (
    "click", "select", "enter", "type", "set", "fill",
    "open", "navigate", "goto", "wait", "get",
    "is", "has", "verify", "assert"
)


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
    # Optional: load existing helper first
    try:
        from tools.llm.env_loader import load_env_local  # type: ignore
        load_env_local(REPO_ROOT)
    except Exception:
        pass

    # FORCE override from .env.local
    _load_env_local_force(REPO_ROOT)

    # Backward compat token var names
    if not os.getenv("LOCAL_LLM_API_KEY"):
        if os.getenv("OPENAI_API_KEY"):
            os.environ["LOCAL_LLM_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        elif os.getenv("DEEPSEEK_API_KEY"):
            os.environ["LOCAL_LLM_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")

    if not os.getenv("LOCAL_LLM_MODEL"):
        os.environ["LOCAL_LLM_MODEL"] = DEFAULT_MODEL

    if not os.getenv("LOCAL_LLM_BASE_URL"):
        raise RuntimeError(
            "Missing LOCAL_LLM_BASE_URL. Put it in .env.local, e.g.\n"
            "LOCAL_LLM_BASE_URL=https://<pod>-8000.proxy.runpod.net\n"
            "LOCAL_LLM_API_KEY=local-vllm"
        )


# =========================
# Hash helpers
# =========================
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# =========================
# Basic helpers
# =========================
def usage_exit() -> None:
    print('Usage: python llm_generate.py "Cancel pending order in Salesforce Order History"')
    sys.exit(2)


def load_contracts() -> str:
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found: {CONTRACT_PATH}")
    return CONTRACT_PATH.read_text(encoding="utf-8")


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
# Cloudflare-safe HTTP (curl)
# =========================
def _curl_json(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 90) -> Dict[str, Any]:
    cmd = ["curl", "-sS", "-X", method, url, "-H", "Accept: application/json"]

    if token.strip():
        cmd += ["-H", f"Authorization: Bearer {token.strip()}"]

    if payload is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(payload)]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"curl timeout calling {url}") from e

    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()

    if r.returncode != 0:
        raise RuntimeError(f"curl failed ({r.returncode}) for {url}\nSTDERR:\n{err}\nSTDOUT:\n{out}")

    try:
        return json.loads(out) if out else {}
    except json.JSONDecodeError:
        raise RuntimeError(f"Non-JSON response from {url}\nSTDOUT:\n{out}\nSTDERR:\n{err}")


def list_models() -> List[str]:
    base = os.environ["LOCAL_LLM_BASE_URL"].rstrip("/")
    token = os.environ.get("LOCAL_LLM_API_KEY", "")
    j = _curl_json("GET", f"{base}/v1/models", token=token, payload=None)
    data = j.get("data", []) or []
    return [m.get("id", "") for m in data if m.get("id")]


def completions(prompt: str, max_tokens: int = 400, temperature: float = 0.0, stop: Optional[List[str]] = None) -> str:
    base = os.environ["LOCAL_LLM_BASE_URL"].rstrip("/")
    token = os.environ.get("LOCAL_LLM_API_KEY", "")
    model = os.environ.get("LOCAL_LLM_MODEL", DEFAULT_MODEL)

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if stop:
        payload["stop"] = stop

    j = _curl_json("POST", f"{base}/v1/completions", token=token, payload=payload)
    choices = j.get("choices", []) or []
    text = choices[0].get("text", "") if choices else ""
    return text or ""


# =========================
# Strict Gherkin (1 Given/When/Then)
# =========================
def extract_strict_5_lines(raw: str) -> str:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    feature = scenario = given = when = then = None

    for s in lines:
        if feature is None and s.startswith("Feature:"):
            feature = s
            continue
        if feature is not None and scenario is None and s.startswith("Scenario:"):
            scenario = s
            continue
        if scenario is not None and given is None and s.startswith("Given "):
            given = s
            continue
        if scenario is not None and when is None and s.startswith("When "):
            when = s
            continue
        if scenario is not None and then is None and s.startswith("Then "):
            then = s
            continue
        if feature and scenario and given and when and then:
            break

    if not (feature and scenario and given and when and then):
        return raw.strip()

    return "\n".join([feature, scenario, given, when, then]).strip()


def validate_llm_output_strict_gherkin(text: str) -> None:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if sum(l.startswith("Given ") for l in lines) != 1:
        raise ValueError("Must have exactly one Given")
    if sum(l.startswith("When ") for l in lines) != 1:
        raise ValueError("Must have exactly one When")
    if sum(l.startswith("Then ") for l in lines) != 1:
        raise ValueError("Must have exactly one Then")
    if not any(l.startswith("Feature:") for l in lines):
        raise ValueError("Missing Feature")
    if not any(l.startswith("Scenario:") for l in lines):
        raise ValueError("Missing Scenario")
    for l in lines:
        if l.startswith("And ") or l.startswith("But "):
            raise ValueError("And/But not allowed")


def normalize_feature_file(text: str) -> str:
    raw = [l.strip() for l in text.splitlines() if l.strip()]
    feature = next(l for l in raw if l.startswith("Feature:"))
    scenario = next(l for l in raw if l.startswith("Scenario:"))
    given = next(l for l in raw if l.startswith("Given "))
    when = next(l for l in raw if l.startswith("When "))
    then = next(l for l in raw if l.startswith("Then "))
    return "\n".join([feature, "", scenario, f"  {given}", f"  {when}", f"  {then}"])


# =========================
# Robust JSON extraction
# =========================
def _strip_code_fences(text: str) -> str:
    t = text.strip()
    t = t.replace("```json", "").replace("```JSON", "").replace("```", "")
    return t.strip()


def extract_first_json_object(raw: str) -> str:
    """
    Extract the first top-level JSON object from a noisy model output.
    Handles leading '.', prose, markdown fences, etc.
    """
    s = _strip_code_fences(raw)

    # fast path
    s2 = s.strip()
    if s2.startswith("{") and s2.endswith("}"):
        return s2

    # find first '{' and then match braces
    start = s.find("{")
    if start == -1:
        raise ValueError("No '{' found in output")

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i + 1].strip()

    raise ValueError("Unbalanced JSON braces in output")


# =========================
# Atomic method name enforcement
# =========================
def _is_allowed_prefix(name: str) -> bool:
    return any(name.startswith(p) for p in ALLOWED_METHOD_PREFIXES)


def _capitalize_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def coerce_atomic_method_name(name: str, method_type: str = "") -> str:
    """
    If model returns non-atomic method name (e.g., confirmCancel),
    rewrite it to an allowed-prefix name (e.g., clickConfirmCancel).
    """
    nm = (name or "").strip()
    if not nm:
        return nm

    if _is_allowed_prefix(nm):
        return nm

    t = (method_type or "").strip().lower()

    # map method "type" to a prefix
    if t in ("nav", "navigate", "navigation"):
        prefix = "navigate"
    elif t in ("click", "button"):
        prefix = "click"
    elif t in ("select", "choose"):
        prefix = "select"
    elif t in ("enter", "input", "type", "fill"):
        prefix = "enter"
    elif t in ("verify", "assert", "check"):
        prefix = "verify"
    else:
        prefix = "click"  # safe default

    return prefix + _capitalize_first(nm)


def ensure_unique(names: List[str]) -> List[str]:
    seen = {}
    out = []
    for n in names:
        base = n
        if base not in seen:
            seen[base] = 1
            out.append(base)
            continue
        seen[base] += 1
        out.append(f"{base}{seen[base]}")
    return out


# =========================
# Granular plan for Steps/Page
# =========================
def plan_granular_steps(task: str, contracts: str, rag_context: str, strict_5: str) -> Dict[str, Any]:
    prompt = f"""
SYSTEM:
You generate a JSON plan for Selenium Page Object + Cucumber Steps.

INPUTS:
- Strict Gherkin (exactly 5 lines) is the contract for the feature file.
- You MUST create granular atomic actions for Page Object methods.

OUTPUT (RETURN ONLY JSON, NO MARKDOWN):
{{
  "page": {{
    "className": "XxxPage",
    "methods": [
      {{"name":"navigateToOrderHistory", "type":"nav", "comment":"Navigate to the Order History page"}},
      {{"name":"selectPendingOrder", "type":"select", "comment":"Select a pending order from the list"}},
      {{"name":"clickCancelOrder", "type":"click", "comment":"Click Cancel Order"}},
      {{"name":"clickConfirmCancel", "type":"click", "comment":"Confirm the cancellation"}}
    ]
  }},
  "steps": {{
    "className": "XxxSteps",
    "givenCalls": ["navigateToOrderHistory"],
    "whenCalls": ["selectPendingOrder", "clickCancelOrder", "clickConfirmCancel"],
    "thenCalls": ["verifyOrderCancelled"]
  }}
}}

RULES:
- method names must be Java identifiers (camelCase), unique.
- IMPORTANT: Every method name MUST start with one of these prefixes:
  {", ".join(ALLOWED_METHOD_PREFIXES)}
- givenCalls/whenCalls/thenCalls MUST reference method names from page.methods.
- Create 2-8 methods total, based on the task.
- Keep it realistic for Salesforce-style UI flows.
- Do NOT output anything except JSON.

CONTRACTS:
{contracts}

RAG CONTEXT (optional):
{rag_context}

STRICT_GHERKIN_5_LINES:
{strict_5}

TASK:
{task}
""".strip()

    raw = completions(prompt, max_tokens=800, temperature=0.0)

    try:
        json_str = extract_first_json_object(raw)
        plan = json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"Could not parse JSON plan from model.\nRAW:\n{raw}") from e

    # minimal structural validation
    if "page" not in plan or "steps" not in plan:
        raise RuntimeError(f"Plan missing 'page' or 'steps'. RAW:\n{raw}")

    methods = plan["page"].get("methods", [])
    if not isinstance(methods, list) or not methods:
        raise RuntimeError(f"Plan page.methods empty. RAW:\n{raw}")

    # ---- enforce atomic + uniqueness + update calls accordingly ----
    old_to_new: Dict[str, str] = {}
    coerced_names: List[str] = []
    for m in methods:
        if not isinstance(m, dict):
            continue
        old = (m.get("name") or "").strip()
        mtype = (m.get("type") or "").strip()
        new = coerce_atomic_method_name(old, mtype)
        coerced_names.append(new)
        old_to_new[old] = new
        m["name"] = new

    # enforce uniqueness (and update mapping)
    unique_names = ensure_unique(coerced_names)
    if unique_names != coerced_names:
        # re-apply unique names in same order
        i = 0
        for m in methods:
            if isinstance(m, dict) and (m.get("name") or "").strip():
                m["name"] = unique_names[i]
                coerced_names[i] = unique_names[i]
                i += 1

    method_names = {m.get("name") for m in methods if isinstance(m, dict)}

    # normalize calls and ensure they reference page.methods
    for k in ["givenCalls", "whenCalls", "thenCalls"]:
        calls = plan["steps"].get(k, [])
        if not isinstance(calls, list) or not calls:
            raise RuntimeError(f"Plan steps.{k} empty. RAW:\n{raw}")

        fixed_calls = []
        for c in calls:
            # map old->new if needed
            cc = old_to_new.get(c, c)
            fixed_calls.append(cc)

        plan["steps"][k] = fixed_calls

    # OPTIONAL safety: if model included something like loginIfNeeded that is not a method,
    # auto-add a placeholder method so validation doesn't blow up.
    # If you *never* want this, delete this whole block.
    for k in ["givenCalls", "whenCalls", "thenCalls"]:
        for c in plan["steps"][k]:
            if c not in method_names:
                # add placeholder atomic method
                placeholder = coerce_atomic_method_name(c, "nav")
                placeholder = placeholder if placeholder not in method_names else f"{placeholder}2"
                methods.append({"name": placeholder, "type": "nav", "comment": f"Placeholder for {c}"})
                method_names.add(placeholder)
                # replace call
                plan["steps"][k] = [placeholder if x == c else x for x in plan["steps"][k]]

    # final validation: calls must exist
    method_names = {m.get("name") for m in methods if isinstance(m, dict)}
    for k in ["givenCalls", "whenCalls", "thenCalls"]:
        for c in plan["steps"][k]:
            if c not in method_names:
                raise RuntimeError(f"steps.{k} references missing method '{c}'. RAW:\n{raw}")

    return plan


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


def _java_method_stub(name: str, comment: str) -> str:
    safe_comment = (comment or "").strip()
    if safe_comment:
        safe_comment = "        // " + safe_comment.replace("\n", " ")
    else:
        safe_comment = "        // TODO: implement atomic action"

    return f"""
    public void {name}() {{
{safe_comment}
    }}
""".rstrip()


def write_page_object(page_class: str, methods: List[Dict[str, Any]]) -> Path:
    ensure_dirs()
    path = GENERATED_PAGES_DIR / f"{page_class}.java"

    method_blocks = []
    for m in methods:
        nm = (m.get("name") or "").strip()
        cm = (m.get("comment") or "").strip()
        if not nm:
            continue
        method_blocks.append(_java_method_stub(nm, cm))

    code = f"""\
package generated.pages;

public class {page_class} {{

{chr(10).join(method_blocks)}

}}
"""
    path.write_text(code, encoding="utf-8")
    return path


def write_steps(steps_class: str, page_class: str, strict_5: str, calls: Dict[str, List[str]]) -> Path:
    ensure_dirs()
    path = GENERATED_STEPS_DIR / f"{steps_class}.java"

    lines = [l.strip() for l in strict_5.splitlines() if l.strip()]
    given_line = next(l for l in lines if l.startswith("Given "))
    when_line = next(l for l in lines if l.startswith("When "))
    then_line = next(l for l in lines if l.startswith("Then "))

    given_text = given_line[len("Given "):].strip()
    when_text = when_line[len("When "):].strip()
    then_text = then_line[len("Then "):].strip()

    def chain(method_list: List[str]) -> str:
        return "\n".join([f"        page.{m}();" for m in method_list])

    code = f"""\
package generated.steps;

import generated.pages.{page_class};
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

public class {steps_class} {{

    private final {page_class} page = new {page_class}();

    @Given("{given_text}")
    public void givenStep() {{
{chain(calls["given"])}
    }}

    @When("{when_text}")
    public void whenStep() {{
{chain(calls["when"])}
    }}

    @Then("{then_text}")
    public void thenStep() {{
{chain(calls["then"])}
    }}
}}
"""
    path.write_text(code, encoding="utf-8")
    return path


def write_meta(meta: Dict[str, Any]) -> None:
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

    models = list_models()
    print("LOCAL_LLM_READY: /v1/models OK")
    print("MODELS:", models[:5], "..." if len(models) > 5 else "")

    rag_results = retrieve(task, top_k=RAG_TOP_K)
    rag_context = "\n".join([f"[{r['doc']}#{r['chunk']}] {r.get('content','')}" for r in rag_results]).strip()
    rag_available = bool(rag_context)
    rag_context_hash = sha256(rag_context) if rag_available else "EMPTY"

    contracts = load_contracts()
    contract_checksum = sha256(contracts)

    strict_prompt = f"""
SYSTEM:
You are a STRICT Gherkin generator.

OUTPUT FORMAT (MUST FOLLOW EXACTLY):
Return EXACTLY 5 non-empty lines:
1) Feature: ...
2) Scenario: ...
3) Given ...
4) When ...
5) Then ...
No other text. No And/But.

CONTRACTS:
{contracts}

RAG CONTEXT (optional):
{rag_context}

TASK:
{task}

REMINDER:
Return ONLY the 5 lines.
""".strip()

    raw1 = completions(strict_prompt, max_tokens=220, temperature=0.0, stop=None)
    strict_5 = extract_strict_5_lines(raw1)

    print("=== RAW LLM OUTPUT START (STRICT 5) ===")
    print(strict_5)
    print("=== RAW LLM OUTPUT END (STRICT 5) ===")

    validate_llm_output_strict_gherkin(strict_5)
    feature_file_text = normalize_feature_file(strict_5)

    feature_name = extract_feature_name(feature_file_text) or task
    class_base = to_pascal_case(feature_name)
    page_class = f"{class_base}Page"
    steps_class = f"{class_base}Steps"

    plan = plan_granular_steps(
        task=task,
        contracts=contracts,
        rag_context=rag_context,
        strict_5=strict_5
    )

    page_class = plan["page"].get("className") or page_class
    steps_class = plan["steps"].get("className") or steps_class
    methods = plan["page"]["methods"]

    calls = {
        "given": plan["steps"]["givenCalls"],
        "when": plan["steps"]["whenCalls"],
        "then": plan["steps"]["thenCalls"],
    }

    feature_path = write_feature(feature_file_text, feature_name)
    page_path = write_page_object(page_class, methods)
    steps_path = write_steps(steps_class, page_class, strict_5, calls)

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
        "generation": {
            "strict_gherkin_5": strict_5,
            "plan": plan,
        },
    }
    write_meta(meta)

    print("PROMPT_VERSION:", PROMPT_VERSION)
    print("CONTRACT_CHECKSUM:", contract_checksum)
    print("RAG_AVAILABLE:", rag_available)
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