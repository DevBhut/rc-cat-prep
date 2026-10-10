"""
Step 5: Generate markdown files from extracted JSONL for OSS contributors.
Input: per-passage data.jsonl
Output: passage.md files
"""

import json
import frontmatter
from pathlib import Path

def main():
    out_dir = Path("scripts/data/passages")
    for folder in sorted(out_dir.glob("passage_*")):
        record = json.loads((folder / "data.jsonl").read_text())

        md = frontmatter.Post(
            record["passage_text"],
            **{
                "id": record["id"],
                "source": record["source"],
                "passage_number": record["passage_number"],
                "total_questions": record["total_questions"]
            }
        )

        body = []
        for q in record.get("questions", []):
            body.append(f"\n### Q{q['question_number']}\n{q['question_text']}\n")
            for opt in ["A", "B", "C", "D", "E"]:
                body.append(f"({opt}) {q['options'].get(opt, '')}\n")
            body.append(f"\n**Correct:** {q.get('correct_option') or 'TBD'}\n")
            body.append(f"**Explanation:** {q.get('explanation') or ''}\n")

        md.content = md.content + "\n\n## Questions\n" + "".join(body)
        (folder / "passage.md").write_text(frontmatter.dumps(md), encoding="utf-8")

    print(f"Generated markdown files in {out_dir}")

if __name__ == "__main__":
    main()
