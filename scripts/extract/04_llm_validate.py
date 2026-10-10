"""
Step 4 (Optional): LLM validation of extracted passages using Ollama.
Input: per-passage data.jsonl + snippet.pdf
Output: validation_log.jsonl
"""

import json
import base64
from pathlib import Path

# import ollama

def validate_passage(folder: Path):
    # TODO: Implement LLM validation
    print(f"Validation not yet implemented for {folder}")

def main():
    out_dir = Path("scripts/data/passages")
    for folder in sorted(out_dir.glob("passage_*")):
        validate_passage(folder)

if __name__ == "__main__":
    main()
