"""
STEP 3: Takes chunks.json and creates a searchable vector database (FAISS).
This converts each text chunk into a list of numbers (embedding) that
represents its meaning, so we can later search by meaning, not just keywords.

Run this AFTER chunk_documents.py has created data/chunks.json

Run with: python rag_engine/build_vector_store.py
"""

import json
import pickle
import os
import faiss
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = "data/chunks.json"
INDEX_FILE = "rag_engine/vector_store.index"
METADATA_FILE = "rag_engine/chunk_metadata.pkl"

MODEL_NAME = "all-MiniLM-L6-v2"  # free, fast, runs on your own laptop


def build_index():
    if not os.path.exists(CHUNKS_FILE):
        print(f"File not found: {CHUNKS_FILE}. Run chunk_documents.py first.")
        return

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("chunks.json is empty. Add some documents first.")
        return

    texts = [c["text"] for c in chunks]

    print("Loading embedding model (first run downloads it, may take a minute)...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Creating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, INDEX_FILE)

    with open(METADATA_FILE, "wb") as f:
        pickle.dump(chunks, f)

    print(f"Done! Vector store saved to {INDEX_FILE}")


if __name__ == "__main__":
    build_index()
