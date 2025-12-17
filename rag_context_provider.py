import os
import sys
from pathlib import Path
from subprocess import run, PIPE

REPO_ROOT = Path(__file__).resolve().parent


def get_llm_context(question: str, k: int = 3) -> str:
    """
    Production RAG provider.
    Fail-open: returns "" on any error.
    Set RAG_DEBUG=1 to print diagnostics locally.
    """
    debug = os.getenv("RAG_DEBUG", "0") == "1"

    try:
        result = run(
            [sys.executable, "rag_retrieve.py", question, str(k)],
            cwd=str(REPO_ROOT),
            stdout=PIPE,
            stderr=PIPE,
            text=True
        )

        if debug:
            print("RAG_DEBUG sys.executable:", sys.executable)
            print("RAG_DEBUG cwd:", str(REPO_ROOT))
            print("RAG_DEBUG returncode:", result.returncode)
            if result.stderr:
                print("RAG_DEBUG stderr:\n", result.stderr)
            if result.stdout:
                print("RAG_DEBUG stdout(first 300):\n", result.stdout[:300])

        if result.returncode != 0:
            return ""

        return (result.stdout or "").strip()

    except Exception as e:
        if debug:
            print("RAG_DEBUG exception:", repr(e))
        return ""