from sentence_transformers import SentenceTransformer
import faiss
import pickle
import sys

model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("rag.index")

with open("rag_sources.pkl", "rb") as f:
    sources = pickle.load(f)

def get_context(query, k=2):
    q_emb = model.encode([query])
    D, I = index.search(q_emb, k)
    context = []
    for idx in I[0]:
        with open(f"rag_docs/{sources[idx]}", encoding="utf-8") as fh:
            context.append(fh.read())
    return "\n\n---\n\n".join(context)

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    if not query.strip():
        print('Usage: python rag_retrieve.py "your question" [k]')
        sys.exit(1)

    print(get_context(query, k))
