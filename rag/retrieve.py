import faiss, pickle
from sentence_transformers import SentenceTransformer

INDEX_DIR = "rag_index"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL)
index = faiss.read_index(f"{INDEX_DIR}/index.faiss")
meta = pickle.load(open(f"{INDEX_DIR}/meta.pkl", "rb"))

def retrieve(query: str, top_k: int = 5):
    q_emb = model.encode([query])
    scores, ids = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], ids[0]):
        m = meta[idx]
        results.append({
            "score": float(score),
            "doc": m["doc"],
            "chunk": m["chunk"],
            "content": m.get("text", "")
        })
    return results

if __name__ == "__main__":
    print(retrieve("order cancellation", top_k=5))