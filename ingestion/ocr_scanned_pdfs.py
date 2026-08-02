"""
OCR SCRIPT for scanned/image-based PDFs (the ones pdfplumber cannot read).

BEFORE RUNNING THIS - install 2 things on your system (not just pip):

1. Tesseract OCR engine:
   Download: https://github.com/UB-Mannheim/tesseract/wiki
   While installing, check the "Marathi" language box (or add mar.traineddata
   to the Tesseract "tessdata" folder afterward)
   Add the Tesseract install folder to your PATH
   (usually C:\\Program Files\\Tesseract-OCR)

2. Poppler (converts PDF pages into images):
   Download: https://github.com/oschwartz10612/poppler-windows/releases
   Extract it anywhere, then add the "bin" folder inside it to your PATH

Then install Python packages (already in requirements.txt):
   pip install pytesseract pdf2image pillow

How to use:
1. Put scanned PDFs inside data/raw_pdfs/ (same folder as your normal PDFs)
2. Run this file - it automatically finds PDFs with no readable text and
   OCRs only those (skips PDFs that already have good text)
3. Then run chunk_documents.py and build_vector_store.py as usual

Run with: python ingestion/ocr_scanned_pdfs.py
"""

import os
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

RAW_PDF_FOLDER = "data/raw_pdfs"
RAW_TEXT_FOLDER = "data/raw_text"

OCR_LANGUAGES = "eng+mar"


def needs_ocr(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:2]:
                text = page.extract_text()
                if text and len(text.strip()) > 30:
                    return False
        return True
    except Exception:
        return True


def ocr_pdf(pdf_path):
    pages = convert_from_path(pdf_path, dpi=300)
    full_text = ""
    for i, page_image in enumerate(pages):
        text = pytesseract.image_to_string(page_image, lang=OCR_LANGUAGES)
        full_text += text + "\n"
        print(f"    OCR'd page {i + 1}/{len(pages)}")
    return full_text


def process_scanned_pdfs():
    os.makedirs(RAW_TEXT_FOLDER, exist_ok=True)

    if not os.path.exists(RAW_PDF_FOLDER):
        print(f"Folder not found: {RAW_PDF_FOLDER}")
        return

    pdf_files = [f for f in os.listdir(RAW_PDF_FOLDER) if f.endswith(".pdf")]

    if not pdf_files:
        print("No PDF files found in data/raw_pdfs/")
        return

    scanned_count = 0

    for filename in pdf_files:
        pdf_path = os.path.join(RAW_PDF_FOLDER, filename)
        txt_filename = filename.replace(".pdf", ".txt")
        txt_path = os.path.join(RAW_TEXT_FOLDER, txt_filename)

        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 200:
            continue

        if needs_ocr(pdf_path):
            print(f"Scanning (OCR): {filename}")
            scanned_count += 1
            try:
                text = ocr_pdf(pdf_path)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"  Done: {txt_filename}")
            except Exception as e:
                print(f"  ERROR OCR'ing {filename}: {e}")

    print(f"\nOCR complete. {scanned_count} scanned document(s) processed.")
    if scanned_count == 0:
        print("(No scanned PDFs found needing OCR - all already have text.)")


if __name__ == "__main__":
    process_scanned_pdfs()
