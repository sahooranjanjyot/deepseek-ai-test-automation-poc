from __future__ import annotations

import os
from pathlib import Path


def load_env_local(repo_root: Path | None = None) -> None:
    """
    Loads KEY=VALUE lines from .env.local into os.environ (if not already set).
    Local-only helper. Safe to keep under tools/llm (git-ignored).
    """
    if repo_root is None:
        # env_loader.py is tools/llm/env_loader.py -> repo root is 2 levels up
        repo_root = Path(__file__).resolve().parents[2]

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
        if k and (k not in os.environ):
            os.environ[k] = v