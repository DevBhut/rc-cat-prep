"""
Step 2: Slice passages using regex heuristics.
Input: pages_index.jsonl
Output: per-passage folders with data.jsonl + snippet.pdf + page images.
"""

import re
import json
import shutil
from pathlib import Path

OUT_DIR = Path("scripts/data/passages")

PASSAGE_MARKER_RE = re.compile(
    r'^\s*#?\s*Passage\s+(\d+)\s*[\(\[\{]?\s*(\d+)\s*/\s*(\d+)\s*[\)\]\}]?',
    re.IGNORECASE | re.MULTILINE
)

QUESTION_START_RE = re.compile(
    r'^\s*(\d+)[\.．]\s*(.*)',
    re.MULTILINE
)

OPTION_RE = re.compile(
    r'^\s*\(([A-Ea-e])\)\s*(.*)',
    re.MULTILINE
)

NOISE_RE = re.compile(
    r'(?:^GMAT(?:,GRE,LSAT\s*阅读)?\s*\d+.*$)|(?:^\s*\d{1,3}\s*$)',
    re.MULTILINE
)

def infer_source(global_id: int) -> str:
    if 1 <= global_id <= 63:   return "GMAT-NEW"
    if 64 <= global_id <= 85:  return "GMAT-22"
    if 86 <= global_id <= 100: return "GMAT-15"
    if 101 <= global_id <= 117: return "OG"
    return "UNKNOWN"

def main():
    # TODO: Implement passage slicing logic from plan
    print("Passage slicing not yet implemented")

if __name__ == "__main__":
    main()
