from sentence_transformers import SentenceTransformer
import faiss
import pickle

model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("rag.index")

with open("rag_sources.pkl", "rb") as f:
    sources = pickle.load(f)

def get_context(query, k=2):
    q_emb = model.encode([query])
    D, I = index.search(q_emb, k)
    context = []
    for idx in I[0]:
        with open(f"rag_docs/{sources[idx]}") as f:
            context.append(f.read())
    return "\n".join(context)
