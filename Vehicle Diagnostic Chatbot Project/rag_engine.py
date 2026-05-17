import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load documents
def load_documents():

    base_dir = os.path.dirname(os.path.abspath(__file__))

    folder = os.path.join(base_dir, "automotive_docs")

    docs = []

    if not os.path.exists(folder):
        print(f"Folder not found: {folder}")
        return ["Automotive diagnostic knowledge base placeholder"]

    for filename in os.listdir(folder):

        filepath = os.path.join(folder, filename)

        if os.path.isfile(filepath):

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

                chunks = content.split("\n\n")

                docs.extend([chunk for chunk in chunks if chunk.strip()])

    if not docs:
        docs = ["Automotive diagnostic knowledge base placeholder"]

    return docs
documents = load_documents()

# TF-IDF vectorization
vectorizer = TfidfVectorizer()
doc_vectors = vectorizer.fit_transform(documents)

# Retrieve relevant context
def retrieve_context(query, top_k=3):

    if not documents:
        return ["No automotive documents found."]

    query_vector = vectorizer.transform([query])

    similarities = cosine_similarity(query_vector, doc_vectors).flatten()

    top_indices = similarities.argsort()[-top_k:][::-1]

    return [documents[i] for i in top_indices]