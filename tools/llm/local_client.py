import json
import os
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


def chat_completion(messages) -> str:
    base = os.getenv("LOCAL_LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LOCAL_LLM_API_KEY", "")
    model = os.getenv("LOCAL_LLM_MODEL", "")

    if not base:
        raise RuntimeError("LOCAL_LLM_BASE_URL is not set")
    if not api_key:
        raise RuntimeError("LOCAL_LLM_API_KEY is not set")
    if not model:
        raise RuntimeError("LOCAL_LLM_MODEL is not set")

    url = f"{base}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
        # Cloudflare/WAF: make request look like a normal browser (curl works, urllib default often blocked)
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    req.add_header("Accept-Language", "en-GB,en;q=0.9")
    req.add_header("Cache-Control", "no-cache")
    req.add_header("Pragma", "no-cache")

    try:
        with urlrequest.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            obj = json.loads(body)
            return obj["choices"][0]["message"]["content"]
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LOCAL_LLM_HTTP_ERROR {e.code}\nURL: {url}\n{body[:500]}") from None
    except URLError as e:
        raise RuntimeError(f"LOCAL_LLM_CONNECTION_ERROR\nURL: {url}\nReason: {e}") from None