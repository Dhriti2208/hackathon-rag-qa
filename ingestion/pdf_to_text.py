"""
STEP 1: Converts PDF files into plain text files.

How to use:
1. Put your downloaded PDFs inside the "data/raw_pdfs" folder
2. Run this file
3. It will create matching .txt files inside "data/raw_text" folder

Run with: python ingestion/pdf_to_text.py
"""

import os
import pdfplumber

RAW_PDF_FOLDER = "data/raw_pdfs"
RAW_TEXT_FOLDER = "data/raw_text"


def convert_pdfs():
    os.makedirs(RAW_TEXT_FOLDER, exist_ok=True)

    if not os.path.exists(RAW_PDF_FOLDER):
        print(f"Folder not found: {RAW_PDF_FOLDER}. Create it and add PDF files first.")
        return

    pdf_files = [f for f in os.listdir(RAW_PDF_FOLDER) if f.endswith(".pdf")]

    if not pdf_files:
        print("No PDF files found yet. Add some PDFs to data/raw_pdfs and run again.")
        return

    for filename in pdf_files:
        pdf_path = os.path.join(RAW_PDF_FOLDER, filename)
        text = ""

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        txt_filename = filename.replace(".pdf", ".txt")
        txt_path = os.path.join(RAW_TEXT_FOLDER, txt_filename)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Converted: {filename} -> {txt_filename}")

    print(f"\nDone! {len(pdf_files)} files converted.")


if __name__ == "__main__":
    convert_pdfs()
