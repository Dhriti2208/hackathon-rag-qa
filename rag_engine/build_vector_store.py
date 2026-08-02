"""
STEP 3: Takes chunks.json and creates a searchable vector database.

If data/metadata.json exists (from extract_metadata.py), this attaches
title, department, date, category, document_number, and language to
EVERY chunk - not just storing metadata separately.

Run with: python rag_engine/build_vector_store.py
"""

import json
import pickle
import os
import faiss
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = "data/chunks.json"
DOC_METADATA_FILE = "data/metadata.json"
INDEX_FILE = "rag_engine/vector_store.index"
METADATA_FILE = "rag_engine/chunk_metadata.pkl"

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def load_doc_metadata_lookup():
    if not os.path.exists(DOC_METADATA_FILE):
        print("Note: data/metadata.json not found - chunks will not have document metadata.")
        print("(Run ingestion/extract_metadata.py first if you want this.)")
        return {}

    with open(DOC_METADATA_FILE, "r", encoding="utf-8") as f:
        doc_list = json.load(f)

    return {d["filename"]: d for d in doc_list}


def build_index():
    if not os.path.exists(CHUNKS_FILE):
        print(f"File not found: {CHUNKS_FILE}. Run chunk_documents.py first.")
        return

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("chunks.json is empty. Add some documents first.")
        return

    doc_metadata_lookup = load_doc_metadata_lookup()

    for chunk in chunks:
        doc_meta = doc_metadata_lookup.get(chunk["source"], {})
        chunk["title"] = doc_meta.get("title", "Unknown")
        chunk["department"] = doc_meta.get("department", "Unknown")
        chunk["date"] = doc_meta.get("date", "Unknown")
        chunk["category"] = doc_meta.get("category", "Other")
        chunk["document_number"] = doc_meta.get("document_number", "Unknown")
        chunk["language"] = doc_meta.get("language", "Unknown")

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
    print("Each chunk now includes: id, source, text, title, department, date, category, document_number, language")


if __name__ == "__main__":
    build_index()
