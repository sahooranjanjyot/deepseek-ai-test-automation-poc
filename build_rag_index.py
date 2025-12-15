from sentence_transformers import SentenceTransformer
import faiss
import os
import pickle

model = SentenceTransformer("all-MiniLM-L6-v2")

docs = []
sources = []

for file in os.listdir("rag_docs"):
    with open(f"rag_docs/{file}") as f:
        text = f.read()
        docs.append(text)
        sources.append(file)

embeddings = model.encode(docs)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, "rag.index")

with open("rag_sources.pkl", "wb") as f:
    pickle.dump(sources, f)

print("✅ RAG index built")
