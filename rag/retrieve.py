# rag/retrieve.py
from pathlib import Path
from typing import List, Dict, Any

import faiss
from sentence_transformers import SentenceTransformer


REPO_ROOT = Path(__file__).resolve().parents[1]

# EXACT files produced by rag_build.py
INDEX_FILE = REPO_ROOT / "rag_index"
SOURCES_FILE = REPO_ROOT / "rag_sources.pkl"
RAG_DOCS_DIR = REPO_ROOT / "rag_docs"

EMBED_MODEL = "all-MiniLM-L6-v2"


def retrieve(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(f"Missing FAISS index file: {INDEX_FILE}")

    if not SOURCES_FILE.exists():
        raise FileNotFoundError(f"Missing sources file: {SOURCES_FILE}")

    # Load index
    index = faiss.read_index(str(INDEX_FILE))

    # Load sources
    import pickle
    sources: List[str] = pickle.loads(SOURCES_FILE.read_bytes())

    # Embed query
    model = SentenceTransformer(EMBED_MODEL)
    qvec = model.encode([query], convert_to_numpy=True)

    k = min(top_k, len(sources))
    distances, ids = index.search(qvec, k)

    results = []
    for rank, idx in enumerate(ids[0]):
        doc_name = sources[idx]
        doc_path = RAG_DOCS_DIR / doc_name

        content = (
            doc_path.read_text(encoding="utf-8", errors="ignore")
            if doc_path.exists()
            else f"[MISSING_DOC] {doc_name}"
        )

        results.append({
            "doc": doc_name,
            "chunk": 0,
            "content": content,
            "score": float(distances[0][rank]),
        })

    return results