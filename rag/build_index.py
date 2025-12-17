from sentence_transformers import SentenceTransformer
import faiss, os, pickle

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DOCS_DIR = "rag_docs"
INDEX_DIR = "rag_index"

os.makedirs(INDEX_DIR, exist_ok=True)

model = SentenceTransformer(MODEL)

texts = []
meta = []

for fname in os.listdir(DOCS_DIR):
    path = os.path.join(DOCS_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        chunks = f.read().split("\n\n")
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if chunk:
                texts.append(chunk)
                meta.append({"doc": fname, "chunk": i, "text": chunk})

embeddings = model.encode(texts)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))
pickle.dump(meta, open(os.path.join(INDEX_DIR, "meta.pkl"), "wb"))

print("RAG index built:", len(texts))