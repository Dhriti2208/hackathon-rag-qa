# How to Run This Project (Final Version)

## One-time setup

1. Install requirements:
```
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and add your Gemini API key
   (get free key from: https://aistudio.google.com/app/apikey)

3. Install Tesseract OCR + Poppler if you have scanned PDFs (see comments
   inside ingestion/ocr_scanned_pdfs.py for download links and setup)

## Full pipeline (run in this exact order)

```
python ingestion/pdf_to_text.py
python ingestion/ocr_scanned_pdfs.py
python ingestion/extract_metadata.py
python ingestion/chunk_documents.py
python rag_engine/build_vector_store.py
streamlit run app/app.py
```

## What each step does

| Step | What it does |
|---|---|
| `pdf_to_text.py` | Converts normal (text-based) PDFs to .txt |
| `ocr_scanned_pdfs.py` | OCRs scanned/image PDFs that step 1 couldn't read |
| `extract_metadata.py` | Uses AI to extract title/department/date/category for each doc |
| `chunk_documents.py` | Breaks all text into small searchable chunks |
| `build_vector_store.py` | Builds the searchable AI database (attaches metadata to chunks) |
| `app.py` | Runs the web app |

## First time using the app

1. Go to the **Register** tab, create a username + password
2. Go to **Log In** tab, log in
3. Ask questions in Tab 1 - try English, Hindi, and Marathi questions
4. Try Tab 2 (Summarize), Tab 3 (Compare), Tab 4 (Browse Documents)
5. Log out and log back in - your chat history should still be there

## When new data arrives

Put new PDFs in `data/raw_pdfs/`, then re-run the full pipeline (all 6
commands above) to include them.
