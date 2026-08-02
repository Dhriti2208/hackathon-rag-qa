"""
RAG PIPELINE - FINAL VERSION (with confidence display fix)

CHANGE FROM BEFORE: The confidence score shown to the user is now based
mainly on semantic (meaning) similarity, not the raw hybrid search score.
Hybrid search still improves WHICH chunks get retrieved (semantic + keyword
combined for ranking), but the confidence percentage shown to the user
reflects "how well does this match in meaning" - which is more intuitive
and less likely to look artificially low.
"""

import pickle
import json
import re
import os
import faiss
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from langdetect import detect, DetectorFactory
from dotenv import load_dotenv

DetectorFactory.seed = 0

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

INDEX_FILE = "rag_engine/vector_store.index"
METADATA_FILE = "rag_engine/chunk_metadata.pkl"
DOC_METADATA_FILE = "data/metadata.json"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

TOP_K = 5
CONFIDENCE_SCALE = 25       # used internally for ranking/gating (unchanged)
MIN_RELEVANCE_SCORE = 0.20  # if best combined score is below this, say "I don't know"
SEMANTIC_WEIGHT = 0.65      # ranking weight (affects WHICH chunks are picked)
KEYWORD_WEIGHT = 0.35       # ranking weight (affects WHICH chunks are picked)

# Separate weights just for the DISPLAYED confidence % - weighted much more
# toward semantic match, since keyword overlap is often low for natural
# language questions even when the answer is completely correct.
DISPLAY_SEMANTIC_WEIGHT = 0.85
DISPLAY_KEYWORD_WEIGHT = 0.15

embed_model = SentenceTransformer(MODEL_NAME)
index = faiss.read_index(INDEX_FILE)

with open(METADATA_FILE, "rb") as f:
    chunks_metadata = pickle.load(f)

tokenized_corpus = [c["text"].lower().split() for c in chunks_metadata]
bm25_index = BM25Okapi(tokenized_corpus)

if os.path.exists(DOC_METADATA_FILE):
    with open(DOC_METADATA_FILE, "r", encoding="utf-8") as f:
        doc_metadata_list = json.load(f)
    doc_metadata_lookup = {d["filename"]: d for d in doc_metadata_list}
else:
    doc_metadata_list = []
    doc_metadata_lookup = {}

llm = genai.GenerativeModel("gemini-3.1-flash-lite")

SUPERSESSION_PATTERNS = [
    r"in supersession of",
    r"supersedes",
    r"in partial modification of",
    r"amends? (the )?(earlier|previous)",
    r"अधिक्रमण",
    r"अधिक्रमित",
    r"सुधारणा करण्यात येत आहे",
]


def detect_language(text):
    devanagari_count = sum(1 for ch in text if '\u0900' <= ch <= '\u097F')

    if devanagari_count == 0:
        return "English"

    try:
        detected_code = detect(text)
    except Exception:
        detected_code = None

    if detected_code == "hi":
        return "Hindi"
    elif detected_code == "mr":
        return "Marathi"
    else:
        return "Marathi"


def retrieve_chunks(question, top_k=TOP_K):
    query_embedding = embed_model.encode([question])
    semantic_distances, semantic_indices = index.search(query_embedding, top_k * 3)
    semantic_lookup = {int(idx): float(dist) for idx, dist in zip(semantic_indices[0], semantic_distances[0])}

    tokenized_query = question.lower().split()
    bm25_scores = bm25_index.get_scores(tokenized_query)
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k * 3]

    candidate_indices = set(semantic_lookup.keys()) | set(bm25_top_indices)

    combined = []
    for idx in candidate_indices:
        sem_dist = semantic_lookup.get(idx, CONFIDENCE_SCALE * 2)
        sem_score = max(0, 1 - (sem_dist / CONFIDENCE_SCALE))
        keyword_score = bm25_scores[idx] / max_bm25 if max_bm25 > 0 else 0

        # ranking score - determines WHICH chunks get picked
        ranking_score = (SEMANTIC_WEIGHT * sem_score) + (KEYWORD_WEIGHT * keyword_score)

        # display score - determines the % shown to the user (weighted more
        # toward meaning-match so it doesn't look artificially low)
        display_score = (DISPLAY_SEMANTIC_WEIGHT * sem_score) + (DISPLAY_KEYWORD_WEIGHT * keyword_score)

        combined.append((idx, ranking_score, display_score, sem_dist))

    combined.sort(key=lambda x: x[1], reverse=True)
    top_candidates = combined[:top_k]

    results = []
    for idx, ranking_score, display_score, sem_dist in top_candidates:
        chunk = chunks_metadata[idx]
        results.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "distance": sem_dist,
            "ranking_score": ranking_score,
            "relevance_score": round(display_score * 100),
            "title": chunk.get("title", "Unknown"),
            "department": chunk.get("department", "Unknown"),
            "date": chunk.get("date", "Unknown"),
            "category": chunk.get("category", "Other"),
        })
    return results


def get_per_source_scores(retrieved_chunks):
    source_scores = {}
    source_titles = {}
    for chunk in retrieved_chunks:
        src = chunk["source"]
        if src not in source_scores or chunk["relevance_score"] > source_scores[src]:
            source_scores[src] = chunk["relevance_score"]
            source_titles[src] = chunk.get("title", src)

    return [{"source": src, "title": source_titles[src], "relevance_score": score} for src, score in
            sorted(source_scores.items(), key=lambda x: x[1], reverse=True)]


def get_all_document_names():
    names = set()
    for chunk in chunks_metadata:
        names.add(chunk["source"])
    return sorted(list(names))


def get_metadata_for_source(source_filename):
    return doc_metadata_lookup.get(source_filename, None)


def get_documents_browse_list():
    docs = []
    for filename, meta in doc_metadata_lookup.items():
        docs.append({
            "Title": meta.get("title", filename),
            "Department": meta.get("department", "Unknown"),
            "Date": meta.get("date", "Unknown"),
            "Category": meta.get("category", "Other"),
            "Language": meta.get("language", "Unknown"),
            "Filename": filename
        })
    return sorted(docs, key=lambda x: (x["Category"], x["Title"]))


def detect_supersession(context_text):
    flagged_sentences = []
    for pattern in SUPERSESSION_PATTERNS:
        matches = re.finditer(pattern, context_text, re.IGNORECASE)
        for match in matches:
            start = max(0, match.start() - 60)
            end = min(len(context_text), match.end() + 60)
            snippet = context_text[start:end].strip()
            flagged_sentences.append(snippet)
    return flagged_sentences[:3]


def get_related_documents(top_source, top_n=3):
    same_doc_chunks = [c for c in chunks_metadata if c["source"] == top_source]
    if not same_doc_chunks:
        return []

    sample_texts = [c["text"] for c in same_doc_chunks[:3]]
    sample_embedding = embed_model.encode(sample_texts).mean(axis=0).reshape(1, -1)

    distances, indices = index.search(sample_embedding, top_n + 10)

    related = []
    seen = {top_source}

    for idx in indices[0]:
        candidate_source = chunks_metadata[idx]["source"]
        if candidate_source not in seen:
            related.append(candidate_source)
            seen.add(candidate_source)
        if len(related) >= top_n:
            break

    return related


def generate_answer(question):
    retrieved = retrieve_chunks(question)

    if not retrieved or retrieved[0]["ranking_score"] < MIN_RELEVANCE_SCORE:
        return {
            "answer": "I don't have enough information to answer this based on the available documents.",
            "sources": [],
            "confidence": 0,
            "per_source_scores": [],
            "related_documents": [],
            "supersession_flags": [],
            "conflict_detected": False,
            "conflict_explanation": ""
        }

    language = detect_language(question)
    context_text = "\n\n".join(
        [f"[Source: {r['source']}]\n{r['text']}" for r in retrieved]
    )

    prompt = f"""You are a helpful assistant answering questions about HTE department documents.
Some source documents may be in Marathi, Hindi, or English. Understand them regardless of language.

IMPORTANT: The user's question is in {language}. You MUST answer in {language}.
While translating, preserve official Government terms (like GR, CAP, AICTE) as they are.

Use ONLY the context below to answer. If the answer is not in the context, say you don't know
(in {language}).

If the different source documents contain CONFLICTING information (different dates, amounts,
eligibility criteria, or rules for the same thing), add a final line starting exactly with
"CONFLICT DETECTED:" followed by a short explanation of the conflict. If there is no conflict,
do not add this line at all.

Context:
{context_text}

Question: {question}

Give a clear answer and mention which source document supports it."""

    try:
        response = llm.generate_content(prompt)
        answer_text = response.text
    except Exception:
        answer_text = "The system is temporarily busy (rate limit reached). Please wait a moment and try again."

    conflict_detected = False
    conflict_explanation = ""
    if "CONFLICT DETECTED:" in answer_text:
        parts = answer_text.split("CONFLICT DETECTED:")
        answer_text = parts[0].strip()
        conflict_explanation = parts[1].strip()
        conflict_detected = True

    sources = list(set([r["source"] for r in retrieved]))
    per_source_scores = get_per_source_scores(retrieved)
    overall_confidence = retrieved[0]["relevance_score"]
    related_documents = get_related_documents(retrieved[0]["source"])
    supersession_flags = detect_supersession(context_text)

    return {
        "answer": answer_text,
        "sources": sources,
        "confidence": overall_confidence,
        "per_source_scores": per_source_scores,
        "related_documents": related_documents,
        "supersession_flags": supersession_flags,
        "conflict_detected": conflict_detected,
        "conflict_explanation": conflict_explanation
    }


def explain_simply(answer_text, language="English"):
    """Rewrites an answer in VERY short, plain language - strict length limit."""
    prompt = f"""Rewrite the following answer in {language}, in EXACTLY 2-3 short sentences,
using everyday words a common person would understand. No headers, no bullet points,
no extra caveats - just plain flowing text. Be as brief as possible while keeping the
core meaning.

Original answer:
{answer_text}

Simple explanation (2-3 sentences max):"""

    try:
        response = llm.generate_content(prompt)
        return response.text
    except Exception:
        return "The system is temporarily busy. Please try again in a moment."


def summarize_document(document_name, max_chunks=15):
    matching_chunks = [c for c in chunks_metadata if c["source"] == document_name]

    if not matching_chunks:
        return {"summary": "Document not found in the system.", "source": document_name}

    matching_chunks = matching_chunks[:max_chunks]
    full_text = "\n\n".join([c["text"] for c in matching_chunks])

    prompt = f"""You are a helpful assistant. Summarize the following Government document
in clear, simple language. Keep the summary concise (under 200 words) and mention
the key points, dates, and rules if present. If the document is in Marathi or Hindi,
you may summarize in English for clarity, but mention important terms in their original form.

Document: {document_name}

Content:
{full_text}

Summary:"""

    try:
        response = llm.generate_content(prompt)
        summary_text = response.text
    except Exception:
        summary_text = "The system is temporarily busy (rate limit reached). Please wait a moment and try again."

    return {"summary": summary_text, "source": document_name}


def compare_documents(doc1_name, doc2_name, max_chunks_each=8):
    doc1_chunks = [c["text"] for c in chunks_metadata if c["source"] == doc1_name][:max_chunks_each]
    doc2_chunks = [c["text"] for c in chunks_metadata if c["source"] == doc2_name][:max_chunks_each]

    if not doc1_chunks or not doc2_chunks:
        return {"comparison": "One or both documents were not found in the system."}

    doc1_text = "\n\n".join(doc1_chunks)
    doc2_text = "\n\n".join(doc2_chunks)

    prompt = f"""You are a helpful assistant comparing two Government documents.
Highlight the KEY DIFFERENCES between them in a clear bullet-point list.
Also mention if one document appears to supersede, amend, or reference the other.
If both documents are largely about the same topic but differ in dates, rules, or
eligibility criteria, point that out clearly.

Document 1: {doc1_name}
Content:
{doc1_text}

Document 2: {doc2_name}
Content:
{doc2_text}

Comparison:"""

    try:
        response = llm.generate_content(prompt)
        comparison_text = response.text
    except Exception:
        comparison_text = "The system is temporarily busy (rate limit reached). Please wait a moment and try again."

    return {"comparison": comparison_text}


if __name__ == "__main__":
    q = input("Ask a question: ")
    result = generate_answer(q)
    print("\nAnswer:", result["answer"])
    print("Sources:", result["sources"])
    print("Overall confidence:", result["confidence"], "%")
    print("Per-source scores:", result["per_source_scores"])
