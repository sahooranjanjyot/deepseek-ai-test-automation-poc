# tools/llm/local_client.py
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Union

import requests

# Env contract (keep stable across local / RunPod / AWS later)
# - LOCAL_LLM_BASE_URL: e.g. "https://<pod>-8000.proxy.runpod.net"  (NO /v1 needed, we'll normalize)
# - LOCAL_LLM_API_KEY: e.g. "local-vllm"
# - LOCAL_LLM_MODEL:   e.g. "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct" OR "deepseek-v2-lite-lora-merged"
# - LOCAL_LLM_TIMEOUT_SECS: optional, default 60
# - LOCAL_LLM_RETRIES: optional, default 2
DEFAULT_TIMEOUT_SECS = float(os.getenv("LOCAL_LLM_TIMEOUT_SECS", "60"))
DEFAULT_RETRIES = int(os.getenv("LOCAL_LLM_RETRIES", "2"))


def _normalize_base_url(raw: str) -> str:
    """
    Accepts:
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
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; DeepSeek-Test-Automation/1.0)",
    }
    key = _api_key()
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def _url(path: str) -> str:
    base = _base_v1()
    if not base:
        return ""
    path = path.lstrip("/")
    return f"{base}/{path}"


def _raise_http_error(resp: requests.Response, url: str) -> None:
    try:
        txt = resp.text or ""
    except Exception:
        txt = ""
    snippet = txt[:2000]
    raise RuntimeError(
        f"LOCAL_LLM_HTTP_ERROR {resp.status_code}\nURL: {url}\nRESPONSE:\n{snippet}"
    )


def list_models(timeout: float = DEFAULT_TIMEOUT_SECS, retries: int = DEFAULT_RETRIES) -> List[Dict[str, Any]]:
    url = _url("models")
    if not url:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_BASE_URL is empty")

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=_headers(), timeout=timeout)
            if r.status_code != 200:
                _raise_http_error(r, url)
            data = r.json()
            return data.get("data", []) or []
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
            else:
                raise

    raise last_err or RuntimeError("LOCAL_LLM_UNKNOWN_ERROR")


def _completion(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: float = DEFAULT_TIMEOUT_SECS,
    retries: int = DEFAULT_RETRIES,
) -> str:
    """
    Calls OpenAI-compatible endpoint:
      POST /v1/completions

    Returns text as a string.
    """
    url = _url("completions")
    if not url:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_BASE_URL is empty")

    use_model = (model or os.getenv("LOCAL_LLM_MODEL", "")).strip()
    if not use_model:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_MODEL is empty")

    payload: Dict[str, Any] = {
        "model": use_model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=timeout)
            if r.status_code != 200:
                _raise_http_error(r, url)

            j = r.json()
            # OpenAI-compatible shape: choices[0].text
            try:
                return j["choices"][0]["text"]
            except Exception:
                compact = json.dumps(j, ensure_ascii=False)[:2000]
                raise RuntimeError(f"LOCAL_LLM_BAD_RESPONSE\nURL: {url}\nRESPONSE:\n{compact}")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
            else:
                raise

    raise last_err or RuntimeError("LOCAL_LLM_UNKNOWN_ERROR")


def chat_completion(
    messages: Union[str, List[Dict[str, str]]],
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: float = DEFAULT_TIMEOUT_SECS,
    retries: int = DEFAULT_RETRIES,
) -> str:
    """
    If caller passes a STRING prompt (your llm_generate.py does),
    we use /v1/completions to avoid chat_template issues.

    If caller passes structured messages, we call /v1/chat/completions.
    """
    # ✅ Key change: string prompts go to /completions (no chat_template needed)
    if isinstance(messages, str):
        return _completion(
            prompt=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            retries=retries,
        )

    url = _url("chat/completions")
    if not url:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_BASE_URL is empty")

    use_model = (model or os.getenv("LOCAL_LLM_MODEL", "")).strip()
    if not use_model:
        raise RuntimeError("LOCAL_LLM_NOT_CONFIGURED: LOCAL_LLM_MODEL is empty")

    payload: Dict[str, Any] = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=timeout)
            if r.status_code != 200:
                _raise_http_error(r, url)

            j = r.json()
            try:
                return j["choices"][0]["message"]["content"]
            except Exception:
                compact = json.dumps(j, ensure_ascii=False)[:2000]
                raise RuntimeError(f"LOCAL_LLM_BAD_RESPONSE\nURL: {url}\nRESPONSE:\n{compact}")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
            else:
                raise

    raise last_err or RuntimeError("LOCAL_LLM_UNKNOWN_ERROR")