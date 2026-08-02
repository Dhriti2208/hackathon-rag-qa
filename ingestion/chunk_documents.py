"""
STEP 2: Reads text files and breaks them into small chunks (pieces).

How to use:
1. Make sure .txt files exist inside "data/raw_text" folder
2. Run this file
3. It saves all chunks into "data/chunks.json"

Run with: python ingestion/chunk_documents.py
"""

import os
import json

RAW_TEXT_FOLDER = "data/raw_text"
OUTPUT_FILE = "data/chunks.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


def process_all_files():
    all_chunks = []

    if not os.path.exists(RAW_TEXT_FOLDER):
        print(f"Folder not found: {RAW_TEXT_FOLDER}. Create it and add .txt files first.")
        return

    txt_files = [f for f in os.listdir(RAW_TEXT_FOLDER) if f.endswith(".txt")]

    if not txt_files:
        print("No .txt files found. Add some text files to data/raw_text and run again.")
        return

    for filename in txt_files:
        filepath = os.path.join(RAW_TEXT_FOLDER, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{filename}_{i}",
                "source": filename,
                "text": chunk
            })

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Done! {len(all_chunks)} chunks from {len(txt_files)} files saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    process_all_files()
