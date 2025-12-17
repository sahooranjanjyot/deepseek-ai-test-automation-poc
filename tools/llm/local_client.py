import json
import os
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

def local_chat(prompt: str, repo_root: Path) -> str:
    """
    Calls local vLLM (RunPod proxy) using OpenAI-compatible API.
    Cloudflare-safe headers included.
    """

    base = os.getenv("LOCAL_LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LOCAL_LLM_API_KEY", "")
    model = os.getenv("LOCAL_LLM_MODEL")

    if not base:
        raise RuntimeError("LOCAL_LLM_BASE_URL is not set")
    if not api_key:
        raise RuntimeError("LOCAL_LLM_API_KEY is not set")
    if not model:
        raise RuntimeError("LOCAL_LLM_MODEL is not set")

    url = f"{base}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 800
    }

    data = json.dumps(payload).encode("utf-8")

    req = urlrequest.Request(url, data=data, method="POST")

    # 🔑 CRITICAL: Cloudflare-safe headers
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            obj = json.loads(body)
            return obj["choices"][0]["message"]["content"]

    except HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"LOCAL_LLM_HTTP_ERROR {e.code}\nURL: {url}\n{body[:500]}"
        ) from None

    except URLError as e:
        raise RuntimeError(
            f"LOCAL_LLM_CONNECTION_ERROR\nURL: {url}\nReason: {e}"
        ) from None