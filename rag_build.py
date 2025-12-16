from pathlib import Path
import pickle
import hashlib

import faiss
from sentence_transformers import SentenceTransformer


RAG_DOCS_DIR = Path("rag_docs")
INDEX_PATH = Path("rag_index")
SOURCES_PATH = Path("rag_sources.pkl")

DRIFT_MARKER = Path("rag_contracts.sha256")
CONTRACTS_SOURCE = RAG_DOCS_DIR / "contracts.md"

MODEL_NAME = "all-MiniLM-L6-v2"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_sources():
    files = sorted([p for p in RAG_DOCS_DIR.glob("*.*") if p.is_file()])
    allowed = {".md", ".txt"}
    files = [p for p in files if p.suffix.lower() in allowed]
    return files


def main():
    if not RAG_DOCS_DIR.exists():
        raise FileNotFoundError(f"Missing folder: {RAG_DOCS_DIR.resolve()}")

    if not CONTRACTS_SOURCE.exists():
        raise FileNotFoundError(f"Missing required contracts source: {CONTRACTS_SOURCE.resolve()}")

    files = load_sources()
    if not files:
        raise RuntimeError("No documents found in rag_docs (.md/.txt)")

    model = SentenceTransformer(MODEL_NAME)

    texts = [p.read_text(encoding="utf-8", errors="ignore") for p in files]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))

    sources = [p.name for p in files]
    with open(SOURCES_PATH, "wb") as f:
        pickle.dump(sources, f)

    # --- DRIFT MARKER ---
    marker_hash = sha256_file(CONTRACTS_SOURCE)
    DRIFT_MARKER.write_text(marker_hash, encoding="utf-8")

    print("RAG_BUILD_COMPLETE")
    print("Indexed:", len(sources))
    print("Wrote:", INDEX_PATH)
    print("Wrote:", SOURCES_PATH)
    print("Wrote:", DRIFT_MARKER)
    print("ContractsSHA:", marker_hash)
    print("Sources:", sources)


if __name__ == "__main__":
    main()