"""
METADATA EXTRACTION (with retry + delay to avoid rate-limit failures)

For each document, this asks the LLM to figure out: title, department,
date, category, and document number. Saves everything into data/metadata.json

FIX: Previously, running this on many documents back-to-back hit the free
API rate limit (5 requests/minute), causing most calls to fail silently
and fall back to "Unknown". Now it: waits between calls, retries failed
calls up to 3 times with increasing delay, and is more robust at parsing
the AI's response even if it adds extra text around the JSON.

Run this AFTER pdf_to_text.py (and ocr_scanned_pdfs.py if you used it).
Run with: python ingestion/extract_metadata.py
"""

import os
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

RAW_TEXT_FOLDER = "data/raw_text"
OUTPUT_FILE = "data/metadata.json"

llm = genai.GenerativeModel("gemini-3.1-flash-lite")

DELAY_BETWEEN_CALLS = 3     # seconds to wait between each document (avoids rate limit)
MAX_RETRIES = 3             # how many times to retry a failed call
RETRY_BACKOFF_SECONDS = 15  # wait this long (x retry number) before retrying


def detect_language_from_text(text):
    devanagari_count = sum(1 for ch in text if '\u0900' <= ch <= '\u097F')
    return "Marathi/Hindi" if devanagari_count > 20 else "English"


def extract_json_from_response(raw_text):
    """Pulls out just the {...} JSON block even if the AI added extra text around it."""
    raw_text = raw_text.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    # find the first { and the last } to isolate the JSON object
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1:
        raw_text = raw_text[start:end + 1]

    return json.loads(raw_text)


def extract_metadata_for_file(filename, text):
    language = detect_language_from_text(text)
    sample_text = text[:1500]

    prompt = f"""Extract metadata from this Government document excerpt.
Respond ONLY in valid JSON format, nothing else, with these exact keys:
{{
  "title": "short descriptive title of the document",
  "department": "issuing department/authority if mentioned, else Unknown",
  "date": "date mentioned in document if any, as written, else Unknown",
  "category": "one of: Scholarship, Admission, Examination, Circular, GR, Notification, Other",
  "document_number": "GR/circular number if mentioned, else Unknown"
}}

Document text:
{sample_text}"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = llm.generate_content(prompt)
            metadata = extract_json_from_response(response.text)
            metadata["filename"] = filename
            metadata["language"] = language
            return metadata
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_SECONDS * attempt
                print(f"    Attempt {attempt} failed ({e}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    All {MAX_RETRIES} attempts failed for {filename}. Using fallback.")

    # fallback if all retries failed
    return {
        "title": filename,
        "department": "Unknown",
        "date": "Unknown",
        "category": "Other",
        "document_number": "Unknown",
        "filename": filename,
        "language": language
    }


def process_all_files():
    if not os.path.exists(RAW_TEXT_FOLDER):
        print(f"Folder not found: {RAW_TEXT_FOLDER}")
        return

    txt_files = [f for f in os.listdir(RAW_TEXT_FOLDER) if f.endswith(".txt")]

    if not txt_files:
        print("No .txt files found. Run pdf_to_text.py first.")
        return

    all_metadata = []

    for i, filename in enumerate(txt_files):
        filepath = os.path.join(RAW_TEXT_FOLDER, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        if len(text.strip()) < 20:
            print(f"[{i + 1}/{len(txt_files)}] Skipping (empty file): {filename}")
            continue

        print(f"[{i + 1}/{len(txt_files)}] Extracting metadata: {filename}")
        metadata = extract_metadata_for_file(filename, text)
        all_metadata.append(metadata)

        # save progress after every file, so a crash partway through doesn't lose everything
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)

        time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\nDone! Metadata for {len(all_metadata)} documents saved to {OUTPUT_FILE}")

    unknown_count = sum(1 for m in all_metadata if m["department"] == "Unknown")
    if unknown_count > 0:
        print(f"Note: {unknown_count} document(s) still show 'Unknown' department "
              f"(likely documents where the text didn't clearly state a department, or repeated failures).")


if __name__ == "__main__":
    process_all_files()
