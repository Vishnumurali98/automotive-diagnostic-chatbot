import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load documents
def load_documents(folder="automotive_docs"):
    docs = []
    for filename in os.listdir(folder):
        with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
            content = f.read()

            #  CHUNKING
            chunks = content.split("\n\n")  # split by paragraphs
            docs.extend(chunks)

    return docs

documents = load_documents()

# Create embeddings
doc_embeddings = embed_model.encode(documents)

# Create FAISS index
dimension = doc_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(doc_embeddings))

def retrieve_context(query, top_k=3):
    query_embedding = embed_model.encode([query])
    distances, indices = index.search(np.array(query_embedding), top_k)
    return [documents[i] for i in indices[0]]