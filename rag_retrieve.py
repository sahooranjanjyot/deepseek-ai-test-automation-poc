import os
import sys
import pickle
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Force UTF-8 output on Windows consoles to avoid UnicodeEncodeError (e.g., '→')
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAG_DOCS_DIR = Path("rag_docs")
INDEX_PATH = Path("rag_index")
SOURCES_PATH = Path("rag_sources.pkl")

MODEL_NAME = "all-MiniLM-L6-v2"


def build_if_missing():
    if INDEX_PATH.exists() and SOURCES_PATH.exists():
        return

    files = sorted([p for p in RAG_DOCS_DIR.glob("*.*") if p.is_file() and p.suffix.lower() in {".md", ".txt"}])
    if not files:
        raise RuntimeError("No documents found in rag_docs (.md/.txt)")

    model = SentenceTransformer(MODEL_NAME)
    texts = [p.read_text(encoding="utf-8", errors="ignore") for p in files]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))

    sources = [p.name for p in files]
    with open(SOURCES_PATH, "wb") as f:
        pickle.dump(sources, f)


def get_context(query: str, k: int = 3) -> str:
    build_if_missing()

    with open(SOURCES_PATH, "rb") as f:
        sources = pickle.load(f)

    index = faiss.read_index(str(INDEX_PATH))
    model = SentenceTransformer(MODEL_NAME)

    q = model.encode([query], convert_to_numpy=True)
    D, I = index.search(np.array(q), k)

    chunks = []
    for idx in I[0]:
        if idx < 0 or idx >= len(sources):
            continue
        p = RAG_DOCS_DIR / sources[idx]
        if p.exists():
            chunks.append(p.read_text(encoding="utf-8", errors="ignore").strip())

    return "\n\n---\n\n".join([c for c in chunks if c])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python rag_retrieve.py "your question" [k]')
        sys.exit(2)

    query = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    print(get_context(query, k))