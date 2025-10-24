import os
import pytesseract
from pdf2image import convert_from_path

# -------- CONFIGURATION --------
PDF_FILE = r"C:\Final LY_project\LY-proj-Flask\ocr\Documents\UED_notes.pdf"  # <-- change this to your actual path
OUTPUT_FILE = r"C:\Final LY_project\LY-proj-Flask\ocr\ocr_output\ocr_output.txt"
LANGUAGE = "eng+hin+mar"  # English + Hindi + Marathi
# --------------------------------

# --- IMPORTANT: Set up paths ---
# 1. Set Tesseract executable path (where tesseract.exe is installed)
# Usually: "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Shubham\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# 2. Poppler path for pdf2image (required to convert PDF → images)
# You must download poppler for Windows from: https://github.com/oschwartz10612/poppler-windows/releases/
# and extract it somewhere, then point to the /bin folder:
POPPLER_PATH = r"C:\Final LY_project\LY-proj-Flask\ocr\poppler-24.07.0\Library\bin"  # update if different
# --------------------------------

def ocr_pdf(pdf_path, lang="eng+hin+mar"):
    """Convert PDF to text using OCR."""
    text_content = []
    try:
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
        total_pages = len(pages)
        for i, page in enumerate(pages, start=1):
            text = pytesseract.image_to_string(page, lang=lang)
            text_content.append(f"\n--- Page {i} ---\n{text}")
            print(f"✅ Processed page {i}/{total_pages}")
    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {e}")
    return "\n".join(text_content)

def main():
    if not os.path.exists(PDF_FILE):
        print(f"❌ PDF file not found: {PDF_FILE}")
        return

    print(f"🔍 Starting OCR on {PDF_FILE} (languages: {LANGUAGE})...")
    text = ocr_pdf(PDF_FILE, lang=LANGUAGE)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n✅ OCR completed. Text saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
