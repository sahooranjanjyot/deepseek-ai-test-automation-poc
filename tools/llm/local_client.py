# tools/llm/local_client.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Union

import requests

DEFAULT_TIMEOUT_SECS = float(os.getenv("LOCAL_LLM_TIMEOUT_SECS", "60"))
DEFAULT_USER_AGENT = os.getenv(
    "LOCAL_LLM_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChatClient/1.0",
)


def _normalize_base_url(raw: str) -> str:
    """
    Accepts any of these:
      - https://host:8000
      - https://host:8000/
      - https://host:8000/v1
      - https://host:8000/v1/
    Returns:
      - https://host:8000/v1
    """
    raw = (raw or "").strip().strip('"').strip("'").rstrip("/")
    if not raw:
        return ""
    if raw.endswith("/v1"):
        return raw
    if raw.endswith("/v1/"):
        return raw[:-1]
    return raw + "/v1"


def _base_v1() -> str:
    return _normalize_base_url(os.getenv("LOCAL_LLM_BASE_URL", ""))


def _api_key() -> str:
    return (os.getenv("LOCAL_LLM_API_KEY", "") or "").strip().strip('"').strip("'")


def _headers() -> Dict[str, str]:
    h: Dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json",
    }
    key = _api_key()
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def _url(path: str) -> str:
    base = _base_v1()
    if not base:
        return ""
    path = (path or "").lstrip("/")
    return f"{base}/{path}"


def _raise_http_error(resp: requests.Response, url: str) -> None:
    body = (resp.text or "")[:4000]
    raise RuntimeError(
        f"LOCAL_LLM_HTTP_ERROR {resp.status_code}\n"
        f"URL: {url}\n"
        f"RESPONSE:\n{body}"
    )


def list_models(timeout: float = DEFAULT_TIMEOUT_SECS) -> List[Dict[str, Any]]:
    url = _url("models")
    if not url:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_BASE_URL is empty")

    r = requests.get(url, headers=_headers(), timeout=timeout)
    if r.status_code != 200:
        _raise_http_error(r, url)

    data = r.json()
    return data.get("data", [])


def _basename_model_id(model_id: str) -> str:
    s = (model_id or "").strip()
    if not s:
        return ""
    # Handles "/workspace/models/xyz" and "a/b/c"
    return s.split("/")[-1]


def _resolve_model_id(configured: str, models: List[Dict[str, Any]]) -> str:
    """
    vLLM may return model ids like:
      - "deepseek-v2-lite-lora-merged"
      - "/workspace/models/deepseek-coder-v2-lite-lora-merged"

    This resolver tries:
      1) exact match
      2) match by basename (last path component)
      3) match by "endswith" (configured matches end of returned id)
      4) fallback to first model in /v1/models
    """
    configured = (configured or "").strip()
    if not models:
        if configured:
            return configured
        raise RuntimeError("LOCAL_LLM_NO_MODELS: /v1/models returned empty list")

    model_ids = [m.get("id", "") for m in models if isinstance(m, dict) and m.get("id")]

    if configured and configured in model_ids:
        return configured

    if configured:
        c_base = _basename_model_id(configured)
        # basename match
        for mid in model_ids:
            if _basename_model_id(mid) == c_base:
                return mid
        # suffix match (handles "/workspace/models/<id>")
        for mid in model_ids:
            if mid.endswith(configured) or mid.endswith(c_base):
                return mid

    # fallback
    return model_ids[0]


def chat_completion(
    messages: Union[str, List[Dict[str, str]]],
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: float = DEFAULT_TIMEOUT_SECS,
) -> str:
    """
    Calls vLLM OpenAI-compatible endpoint:
      POST /v1/chat/completions
    Returns assistant message content as a string.
    """
    url = _url("chat/completions")
    if not url:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_BASE_URL is empty")

    if isinstance(messages, str):
        msgs = [{"role": "user", "content": messages}]
    else:
        msgs = messages

    configured_model = (model or os.getenv("LOCAL_LLM_MODEL", "")).strip()
    models = list_models(timeout=timeout)
    use_model = _resolve_model_id(configured_model, models)

    payload: Dict[str, Any] = {
        "model": use_model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    r = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
    if r.status_code != 200:
        _raise_http_error(r, url)

    j = r.json()
    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        compact = json.dumps(j, ensure_ascii=False)[:2000]
        raise RuntimeError(f"LOCAL_LLM_BAD_RESPONSE\nURL: {url}\nRESPONSE:\n{compact}")