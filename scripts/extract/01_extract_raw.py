"""
Step 1: Extract raw text and images from PDF using pdfplumber + PyMuPDF.
Output: scripts/data/passages/pages_index.jsonl + page images.
"""

import pdfplumber
import fitz
import json
from pathlib import Path

PDF_PATH = Path("PDFS/1000_RC.pdf")
OUT_DIR = Path("scripts/data/passages")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    doc = fitz.open(PDF_PATH)
    pages_meta = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text()

        pix = page.get_pixmap(dpi=200)
        img_path = OUT_DIR / f"page_{i:03d}.png"
        pix.save(img_path)

        pages_meta.append({
            "page_num": i,
            "text": text,
            "image": str(img_path.relative_to(OUT_DIR))
        })

    with open(OUT_DIR / "pages_index.jsonl", "w", encoding="utf-8") as f:
        for p in pages_meta:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Extracted {len(pages_meta)} pages to {OUT_DIR}")

if __name__ == "__main__":
    main()
