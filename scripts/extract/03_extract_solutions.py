"""
Step 3: Extract solutions from pages 992-1004 of the PDF.
Output: scripts/data/passages/solutions.json
"""

import re
import json
from pathlib import Path
import fitz

PDF_PATH = Path("PDFS/1000_RC.pdf")
OUT_DIR = Path("scripts/data/passages")

PASSAGE_MARKER_RE = re.compile(
    r'^\s*#?\s*Passage\s+(\d+)\s*[\(\[\{]?\s*(\d+)\s*/\s*(\d+)\s*[\)\]\}]?',
    re.IGNORECASE | re.MULTILINE
)

ANSWER_LINE_RE = re.compile(
    r'(\d+)\s*[\.．\)]\s*([A-Ea-e])'
)

def main():
    # TODO: Implement solution extraction from pages 992-1004
    print("Solution extraction not yet implemented")

if __name__ == "__main__":
    main()
