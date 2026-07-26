"""
STEP 4: The main RAG pipeline (the "brain" of the project).

Given a user's question, this file:
1. Finds the most relevant document chunks from the vector store
2. Sends those chunks + the question to the LLM (Gemini)
3. Returns an answer PLUS the source documents it used

If nothing relevant is found, it says "I don't know" instead of
making up an answer (this is called avoiding "hallucination").
"""

import pickle
import faiss
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

INDEX_FILE = "rag_engine/vector_store.index"
METADATA_FILE = "rag_engine/chunk_metadata.pkl"
MODEL_NAME = "all-MiniLM-L6-v2"

TOP_K = 5                    # how many chunks to retrieve per question
MAX_DISTANCE = 1.5             # if best match score is worse than this, say "I don't know"
# NOTE: tune MAX_DISTANCE after testing with real questions —
# lower distance = more similar. If answers seem wrong, lower this number.
# If it says "I don't know" too often, raise this number.

embed_model = SentenceTransformer(MODEL_NAME)
index = faiss.read_index(INDEX_FILE)

with open(METADATA_FILE, "rb") as f:
    chunks_metadata = pickle.load(f)

llm = genai.GenerativeModel("gemini-3.5-flash")


def retrieve_chunks(question, top_k=TOP_K):
    query_embedding = embed_model.encode([question])
    distances, indices = index.search(query_embedding, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        chunk = chunks_metadata[idx]
        results.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "distance": float(dist)
        })
    return results


def generate_answer(question):
    retrieved = retrieve_chunks(question)

    if not retrieved or retrieved[0]["distance"] > MAX_DISTANCE:
        return {
            "answer": "I don't have enough information to answer this based on the available documents.",
            "sources": []
        }

    context_text = "\n\n".join(
        [f"[Source: {r['source']}]\n{r['text']}" for r in retrieved]
    )

    prompt = f"""You are a helpful assistant answering questions about HTE department documents.
Use ONLY the context below to answer. If the answer is not in the context, say you don't know.

Context:
{context_text}

Question: {question}

Give a clear answer and mention which source document supports it."""

    response = llm.generate_content(prompt)

    sources = list(set([r["source"] for r in retrieved]))

    return {
        "answer": response.text,
        "sources": sources
    }


if __name__ == "__main__":
    # Quick manual test from terminal
    q = input("Ask a question: ")
    result = generate_answer(q)
    print("\nAnswer:", result["answer"])
    print("Sources:", result["sources"])
