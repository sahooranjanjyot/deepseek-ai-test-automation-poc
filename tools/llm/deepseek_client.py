import json
import ssl
import urllib.request
from pathlib import Path
import os
from tools.llm.env_loader import load_env_local
import certifi

def deepseek_chat(prompt: str, repo_root: Path) -> str:
    load_env_local(repo_root)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not found")

    url = "https://api.deepseek.com/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a test automation generator. Follow contracts strictly."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    context = ssl.create_default_context(cafile=certifi.where())

    with urllib.request.urlopen(req, context=context, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["choices"][0]["message"]["content"]