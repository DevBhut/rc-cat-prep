Here is the complete, implementation-ready plan. You can hand this directly to your coding agent.

---

# RC CAT Prep App — Implementation Plan

## 1. Architecture & Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Framework** | Next.js 15 (App Router) + TypeScript | Full-stack on Vercel; API routes + Server Components in one repo |
| **Database** | **Vercel Postgres** (Serverless PostgreSQL) | Free tier, native Vercel integration, relational for structured RC data |
| **ORM/Client** | `@vercel/postgres` (serverless driver) + raw SQL | Zero-config on Vercel, lightweight |
| **Auth** | Custom JWT (password + one-time OTP) | `bcryptjs` for hashing, `resend` for OTP email, `jose` for JWT |
| **Session** | HTTP-only cookie `session_token` | 14-day `maxAge`, refreshed on activity |
| **Styling** | Tailwind CSS + `shadcn/ui` | Minimal, mobile-first, easy theming |
| **Charts** | Inline SVG / CSS bars only | Zero dependencies, minimal bundle |
| **PDF Extraction** | Python offline pipeline | `pdfplumber` + heuristics + optional local LLM (Ollama) |
| **Source of Truth** | Markdown files (GitHub) → JSON → Postgres | Markdown for OSS contributors; app reads **only** from DB |

---

## 2. Database Schema (Vercel Postgres)

Run this as `schema.sql`. The design supports revision (multiple attempts per user per passage) while still allowing "hide solved" filtering via the `user_passage_status` table.

```sql
-- 1. USERS
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 2. OTP CODES (signup / password reset)
CREATE TABLE otps (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    purpose VARCHAR(20) DEFAULT 'signup', -- 'signup' | 'reset'
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. PASSAGES
CREATE TABLE passages (
    id SERIAL PRIMARY KEY,              -- Global sequential 1..117
    source VARCHAR(50) NOT NULL,      -- 'GMAT-NEW' | 'GMAT-22' | 'GMAT-15' | 'OG'
    passage_number INTEGER NOT NULL,  -- 1..63, 1..22, 1..15, 1..17 (local to source)
    title VARCHAR(500),
    passage_text TEXT NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, passage_number)
);

-- 4. QUESTIONS
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    passage_id INTEGER REFERENCES passages(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,   -- 1, 2, 3... within the passage
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    option_e TEXT NOT NULL,
    correct_option VARCHAR(1) NOT NULL CHECK (correct_option IN ('A','B','C','D','E')),
    explanation TEXT,                 -- Nullable for current PDF; populated for future PDFs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(passage_id, question_number)
);

-- 5. ATTEMPTS (one row per time a user starts & finishes a passage)
CREATE TABLE attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    passage_id INTEGER REFERENCES passages(id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_time_seconds INTEGER,         -- Timer value at submission
    score INTEGER,                      -- Number of correct answers
    total_questions INTEGER,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. ATTEMPT RESPONSES (individual answers per attempt)
CREATE TABLE attempt_responses (
    id SERIAL PRIMARY KEY,
    attempt_id INTEGER REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    selected_option VARCHAR(1),
    is_correct BOOLEAN,
    time_spent_seconds INTEGER DEFAULT 0,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(attempt_id, question_id)
);

-- 7. USER PASSAGE STATUS (denormalized "latest state" for fast filtering)
CREATE TABLE user_passage_status (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    passage_id INTEGER REFERENCES passages(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'unsolved' CHECK (status IN ('unsolved', 'in_progress', 'solved')),
    best_score INTEGER DEFAULT 0,
    best_time_seconds INTEGER,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    UNIQUE(user_id, passage_id)
);

-- Indexes for performance
CREATE INDEX idx_questions_passage ON questions(passage_id);
CREATE INDEX idx_attempts_user ON attempts(user_id);
CREATE INDEX idx_attempts_passage ON attempts(passage_id);
CREATE INDEX idx_user_passage_status_user ON user_passage_status(user_id);
CREATE INDEX idx_otps_email ON otps(email, created_at DESC);
```

---

## 3. Project File Structure

```
rc-cat-prep/
├── app/                          # Next.js App Router
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── verify-otp/page.tsx
│   ├── (app)/
│   │   ├── dashboard/page.tsx    # Stats + passage list
│   │   ├── passage/[id]/page.tsx # Active solving UI
│   │   ├── passage/[id]/result/page.tsx # Post-submit review
│   │   └── layout.tsx            # App shell with theme toggle
│   ├── api/
│   │   ├── auth/
│   │   │   ├── signup/route.ts
│   │   │   ├── login/route.ts
│   │   │   ├── verify-otp/route.ts
│   │   │   ├── resend-otp/route.ts
│   │   │   └── logout/route.ts
│   │   ├── passage/
│   │   │   ├── route.ts          # List passages
│   │   │   └── [id]/route.ts     # Get single passage + questions
│   │   ├── attempt/
│   │   │   ├── start/route.ts    # Create attempt row
│   │   │   └── submit/route.ts   # Final submission + scoring
│   │   ├── response/
│   │   │   └── route.ts          # Auto-save selected option
│   │   └── progress/
│   │       └── route.ts          # Dashboard stats
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                       # shadcn/ui components
│   ├── passage-reader.tsx        # Left/Top panel: passage text + font controls
│   ├── question-card.tsx         # Right/Bottom panel: one question at a time
│   ├── timer.tsx                 # Count-up timer
│   ├── theme-provider.tsx        # Theme context + localStorage
│   ├── theme-toggle.tsx          # Standard / Reading / Dark
│   ├── passage-list.tsx          # Filterable grid for dashboard
│   ├── stats-cards.tsx           # Accuracy, solved count, avg time
│   └── weekly-chart.tsx          # SVG bar chart
├── lib/
│   ├── db.ts                     # @vercel/postgres client setup
│   ├── auth.ts                   # JWT verify/sign helpers (jose)
│   ├── password.ts               # bcryptjs helpers
│   ├── otp.ts                    # 6-digit code generator
│   └── mail.ts                   # Resend email sender
├── scripts/                      # NOT deployed to Vercel
│   ├── extract/
│   │   ├── 01_extract_raw.py     # pdfplumber → raw chunks
│   │   ├── 02_parse_passages.py  # heuristics/regex → markdown
│   │   ├── 03_extract_solutions.py # pages 992-1004 → answer key map
│   │   └── 04_validate.py      # Check all 117 passages + counts
│   ├── seed/
│   │   ├── markdown_to_json.ts   # Parse .md files → JSON
│   │   └── seed_db.ts            # Insert JSON into Vercel Postgres
│   └── data/                     # Output folder
│       ├── passages/             # 117 .md files (OSS source)
│       └── seed.json             # Flat file for DB seeding
├── middleware.ts                 # Protect /(app) routes, validate JWT
├── .env.local
├── tailwind.config.ts
└── package.json
```

---

## 4. Phase 1: Init & Database Setup

1. **Create Next.js project**
   ```bash
   npx shadcn@latest init --yes --template next --base-color stone
   ```
   (Use `stone` for warm, paper-like neutrals. Perfect for the "Reading" theme.)

2. **Install dependencies**
   ```bash
   npm install @vercel/postgres bcryptjs jose resend
   npm install -D @types/bcryptjs
   ```

3. **Connect Vercel Postgres**
   - In Vercel dashboard: Storage → Create Postgres DB (free Hobby tier).
   - Copy `POSTGRES_URL` to `.env.local`.
   - Test: `lib/db.ts` exports `sql` from `@vercel/postgres`.

4. **Run schema**
   - Create `scripts/seed/schema.sql` (from Section 2 above).
   - Run via Vercel CLI or any Postgres client: `psql $POSTGRES_URL -f schema.sql`.

---

Here is the **updated implementation plan**, with Phase 2 completely rewritten to include the per-passage JSONL + focused page-snippet pipeline, exact regexes, and LLM validation. You can hand this directly to your coding agent.

---

## Phase 2: PDF Extraction, Snippet Generation & LLM Validation (Revised)

### 2.1 Output Folder Structure

Every passage gets its own directory. This keeps text, images, and validation artifacts together for human review and LLM context.

```
scripts/
├── extract/
│   ├── requirements.txt
│   ├── 01_extract_raw.py          # pdfplumber → raw text by page
│   ├── 02_slice_passages.py       # regex heuristics → passage folders
│   ├── 03_extract_solutions.py    # pages 992-1004 → answer key JSON
│   ├── 04_llm_validate.py         # (Optional) Send snippet.pdf + JSONL to LLM
│   └── 05_generate_markdown.py    # passage folders → .md files for GitHub
└── data/
    └── passages/
        ├── passage_001/
        │   ├── data.jsonl           # Single line JSONL (source of truth for seeding)
        │   ├── snippet.pdf          # 1–3 page PDF cut from original (for LLM validation)
        │   └── pages/
        │       ├── p003.png         # Rendered page image (200 DPI)
        │       └── p004.png
        ├── passage_002/
        └── ...
```

**Why `snippet.pdf`?**  
Instead of feeding an LLM the entire 1000-page PDF, `02_slice_passages.py` uses `pymupdf` to extract only the pages that belong to that passage (e.g., pages 3–4). The validator then receives a tiny, focused PDF or its rendered PNGs, eliminating cross-passage confusion.

---

### 2.2 Python Dependencies

`scripts/extract/requirements.txt`
```text
pdfplumber>=0.11
PyMuPDF>=1.24          # fitz, for rendering pages & slicing PDFs
python-frontmatter>=1.0 # only for markdown generation later
ollama>=0.3            # optional, for local LLM validation
```

---

### 2.3 Step 1 — Raw Text & Image Extraction (`01_extract_raw.py`)

Use `pdfplumber` for text (it preserves reading order better than raw PDF miners) and `PyMuPDF` for images.

```python
import pdfplumber, fitz, os, json
from pathlib import Path

PDF_PATH = "1000 RC (2).pdf"
OUT_DIR = Path("scripts/data/passages")
OUT_DIR.mkdir(parents=True, exist_ok=True)

doc = fitz.open(PDF_PATH)
pages_meta = []

for i, page in enumerate(doc, start=1):
    # 1. Extract clean text
    text = page.get_text()
    
    # 2. Render page image at 200 DPI for LLM review
    pix = page.get_pixmap(dpi=200)
    img_path = OUT_DIR / f"page_{i:03d}.png"
    pix.save(img_path)
    
    pages_meta.append({
        "page_num": i,
        "text": text,
        "image": str(img_path.relative_to(OUT_DIR))
    })

# Save intermediate index
with open(OUT_DIR / "pages_index.jsonl", "w", encoding="utf-8") as f:
    for p in pages_meta:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
```

---

### 2.4 Step 2 — Passage Slicing & JSONL Creation (`02_slice_passages.py`)

This is the core parser. It uses **deterministic regex** to find passage boundaries, then slices the original PDF into per-passage `snippet.pdf` files.

#### Exact Regex Patterns

```python
import re

# Passage header: Passage 11(11/63)  or  Passage 64 (1/22)  or  # Passage 101(1/17)
PASSAGE_MARKER_RE = re.compile(
    r'^\s*#?\s*Passage\s+(\d+)\s*[\(\[\{]?\s*(\d+)\s*/\s*(\d+)\s*[\)\]\}]?',
    re.IGNORECASE | re.MULTILINE
)

# Question start: "1.", "6.", "7."  (period or full-width dot, optional space)
QUESTION_START_RE = re.compile(
    r'^\s*(\d+)[\.．]\s*(.*)',
    re.MULTILINE
)

# Options: (A)text, (B) text, (C)text  — allowing missing space
OPTION_RE = re.compile(
    r'^\s*\(([A-Ea-e])\)\s*(.*)',
    re.MULTILINE
)

# Noise to strip: headers like "GMAT 13", "GMAT,GRE,LSAT 阅读 28", standalone page numbers
NOISE_RE = re.compile(
    r'(?:^GMAT(?:,GRE,LSAT\s*阅读)?\s*\d+.*$)|(?:^\s*\d{1,3}\s*$)',
    re.MULTILINE
)
```

#### Slicing Algorithm

```python
def slice_passages(pages_index_path: Path, original_pdf: Path):
    passages = []
    current = None
    
    # Load pages
    pages = [json.loads(l) for l in open(pages_index_path, encoding="utf-8")]
    
    for p in pages:
        page_num = p["page_num"]
        text = p["text"]
        
        # Detect passage markers on this page
        markers = list(PASSAGE_MARKER_RE.finditer(text))
        
        for m in markers:
            # Close previous passage
            if current:
                current["end_page"] = page_num - 1
                passages.append(current)
            
            # Start new passage
            current = {
                "id": int(m.group(1)),
                "local_num": int(m.group(2)),
                "local_total": int(m.group(3)),
                "start_page": page_num,
                "raw_text": text[m.end():],
                "pages": [page_num]
            }
        
        if current and not markers:
            current["raw_text"] += "\n" + text
            current["pages"].append(page_num)
    
    # Close final passage
    if current:
        current["end_page"] = pages[-1]["page_num"]
        passages.append(current)
    
    # --- Now parse each passage into structured JSONL + snippet PDF ---
    doc = fitz.open(original_pdf)
    
    for pas in passages:
        # 1. Clean noise
        clean = NOISE_RE.sub('', pas["raw_text"])
        clean = re.sub(r'\n+', '\n', clean).strip()
        
        # 2. Split passage body from questions
        # Find first occurrence of question "1."
        q1_match = QUESTION_START_RE.search(clean)
        if not q1_match:
            # Some passages might have no questions in the slice (rare), log & skip
            continue
        
        passage_body = clean[:q1_match.start()].strip()
        questions_block = clean[q1_match.start():]
        
        # 3. Parse questions
        questions = []
        q_matches = list(QUESTION_START_RE.finditer(questions_block))
        
        for i, qm in enumerate(q_matches):
            q_start = qm.start()
            q_end = q_matches[i+1].start() if i+1 < len(q_matches) else len(questions_block)
            q_text = questions_block[q_start:q_end].strip()
            
            # Extract options within this question block
            opts = {}
            for om in OPTION_RE.finditer(q_text):
                opts[om.group(1).upper()] = om.group(2).strip()
            
            # Question stem = everything before first option
            first_opt = OPTION_RE.search(q_text)
            stem = q_text[:first_opt.start()].strip() if first_opt else q_text
            
            # Remove the leading "1. " from stem
            stem = QUESTION_START_RE.sub('', stem, count=1).strip()
            
            questions.append({
                "question_number": int(qm.group(1)),
                "question_text": stem,
                "options": opts,
                "correct_option": None,  # populated later from solutions
                "explanation": None
            })
        
        # 4. Build JSONL record
        record = {
            "id": pas["id"],
            "source": infer_source(pas["id"]),  # GMAT-NEW, GMAT-22, GMAT-15, OG
            "passage_number": pas["local_num"],
            "pdf_start_page": pas["start_page"],
            "pdf_end_page": pas["end_page"],
            "title": "",  # leave empty unless explicitly present
            "passage_text": passage_body,
            "total_questions": len(questions),
            "questions": questions
        }
        
        # 5. Write to folder
        folder = OUT_DIR / f"passage_{pas['id']:03d}"
        folder.mkdir(exist_ok=True)
        
        with open(folder / "data.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        # 6. Slice snippet PDF (focused pages only)
        snippet_doc = fitz.open()
        for pn in pas["pages"]:
            snippet_doc.insert_pdf(doc, from_page=pn-1, to_page=pn-1)
        snippet_doc.save(folder / "snippet.pdf")
        snippet_doc.close()
        
        # 7. Copy page images into folder for visual QA
        (folder / "pages").mkdir(exist_ok=True)
        for pn in pas["pages"]:
            src = OUT_DIR / f"page_{pn:03d}.png"
            if src.exists():
                import shutil
                shutil.copy(src, folder / "pages" / f"p{pn:03d}.png")

def infer_source(global_id: int) -> str:
    if 1 <= global_id <= 63:   return "GMAT-NEW"
    if 64 <= global_id <= 85:  return "GMAT-22"
    if 86 <= global_id <= 100: return "GMAT-15"
    if 101 <= global_id <= 117: return "OG"
    return "UNKNOWN"
```

**Key normalization fixes** (based on your PDF excerpt):
- `(C)recurrent` → regex `\(([A-Ea-e])\)\s*(.*)` handles missing space after `)`.
- Questions like `6.The author` (no space after period) → `(\d+)[\.．]\s*` handles optional whitespace.
- Headers like `GMAT 13` or `GMAT,GRE,LSAT 阅读 28` are stripped so they don’t pollute passage text.

---

### 2.5 Step 3 — Solution Extraction (`03_extract_solutions.py`)

Input: pages 992–1004 of the PDF.

```python
SOLUTION_PASSAGE_RE = re.compile(
    r'Passage\s+(\d+)[\s\:\-]*(.?)(?=Passage|\Z)',
    re.IGNORECASE | re.DOTALL
)

ANSWER_LINE_RE = re.compile(
    r'(\d+)\s*[\.．\)]\s*([A-Ea-e])'
)

def extract_solutions(pdf_path: Path, start_page: int, end_page: int):
    doc = fitz.open(pdf_path)
    solutions = {}
    
    for pn in range(start_page, end_page + 1):
        text = doc[pn-1].get_text()
        # Look for blocks like:
        # Passage 1
        # 1. B  2. C  3. A ...
        # or vertical lists
        for m in PASSAGE_MARKER_RE.finditer(text):  # reuse same regex
            pid = int(m.group(1))
            block = text[m.end():]
            # grab until next Passage marker or page end
            next_m = PASSAGE_MARKER_RE.search(block)
            if next_m:
                block = block[:next_m.start()]
            
            answers = {}
            for am in ANSWER_LINE_RE.finditer(block):
                q_num = int(am.group(1))
                ans = am.group(2).upper()
                answers[q_num] = ans
            
            solutions[pid] = answers
    
    with open(OUT_DIR / "solutions.json", "w") as f:
        json.dump(solutions, f, indent=2)
```

After this, run a **merge script** that injects `correct_option` into each `data.jsonl`:

```python
# merge_solutions.py
solutions = json.load(open(OUT_DIR / "solutions.json"))
for folder in sorted(OUT_DIR.glob("passage_*")):
    record = json.loads(open(folder / "data.jsonl").read())
    pid = record["id"]
    if str(pid) in solutions or pid in solutions:
        ans_map = solutions.get(pid) or solutions.get(str(pid))
        for q in record["questions"]:
            q["correct_option"] = ans_map.get(str(q["question_number"])) or ans_map.get(q["question_number"])
    # rewrite
    open(folder / "data.jsonl", "w").write(json.dumps(record, ensure_ascii=False) + "\n")
```

---

### 2.6 Step 4 — LLM Validation (`04_llm_validate.py`)

This step is **offline and optional**. It sends the `snippet.pdf` (or its rendered PNG) plus the extracted JSON to a local LLM (Ollama + LLaVA) or an API to catch OCR drift.

```python
import ollama, json, base64
from pathlib import Path

def validate_passage(folder: Path):
    record = json.loads(open(folder / "data.jsonl").read())
    
    # Convert snippet.pdf first page to base64 PNG for vision model
    doc = fitz.open(folder / "snippet.pdf")
    pix = doc[0].get_pixmap(dpi=150)
    img_b64 = base64.b64encode(pix.tobytes("png")).decode()
    
    prompt = f"""
You are an OCR validator for GMAT reading comprehension.
Below is the extracted JSON for one passage and its original PDF page image.
Check:
1. Is the passage text complete? (No missing paragraphs at start/end)
2. Are all questions present and in correct order?
3. Are all options (A)-(E) present for each question?
4. Is there any garbled text or merged lines?

Extracted JSON:
{json.dumps(record, indent=2)}

Reply ONLY with JSON: {{"valid": true/false, "issues": ["..."]}}
"""
    
    response = ollama.chat(
        model="llava",  # or bakllava, or use GPT-4o if you have an API key
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [img_b64]
        }]
    )
    
    # Parse response and append to validation log
    result = response["message"]["content"]
    # ... save to validation_log.jsonl
```

**Agent instruction:** Run `04_llm_validate.py` after extraction. Any passage with `valid: false` gets flagged for manual review before seeding.

---

### 2.7 Step 5 — Markdown Generation (`05_generate_markdown.py`)

Generates the open-source markdown files exactly as specified in the original plan. The app **never reads these at runtime**; they are for GitHub contributors only.

```python
import json, frontmatter
from pathlib import Path

for folder in sorted(Path("scripts/data/passages").glob("passage_*")):
    record = json.loads(open(folder / "data.jsonl").read())
    
    md = frontmatter.Post(
        record["passage_text"],
        **{
            "id": record["id"],
            "source": record["source"],
            "passage_number": record["passage_number"],
            "total_questions": record["total_questions"]
        }
    )
    
    # Append questions
    body = []
    for q in record["questions"]:
        body.append(f"\n### Q{q['question_number']}\n{q['question_text']}\n")
        for opt in ["A","B","C","D","E"]:
            body.append(f"({opt}) {q['options'][opt]}\n")
        body.append(f"\n**Correct:** {q['correct_option'] or 'TBD'}\n")
        body.append(f"**Explanation:** {q['explanation'] or ''}\n")
    
    md.content = md.content + "\n\n## Questions\n" + "".join(body)
    
    open(folder / "passage.md", "w", encoding="utf-8").write(frontmatter.dumps(md))
```

---


## 6. Phase 3: Authentication System

### 6.1 Flow

| Step | Action |
|------|--------|
| **Signup** | User enters Email + Password → API creates user with `is_verified=false` → sends 6-digit OTP via Resend → user enters OTP → `is_verified=true` → JWT cookie set (14 days) |
| **Login** | Email + Password → check `is_verified` → JWT cookie set (14 days) |
| **Session** | `middleware.ts` reads `session_token` cookie, verifies JWT with `jose`, attaches `user` to request |
| **Resend OTP** | Rate-limited: max 3 requests/hour per email |

### 6.2 API Routes

- `POST /api/auth/signup` — `bcryptjs.hash(password, 10)`, insert user, generate OTP, send email.
- `POST /api/auth/verify-otp` — check `otps` table (unused + not expired), set `is_verified=true`, issue JWT.
- `POST /api/auth/login` — verify password, check `is_verified`, issue JWT.
- `POST /api/auth/resend-otp` — generate new OTP, update table, send email.
- `POST /api/auth/logout` — clear cookie.

### 6.3 JWT & Cookie

```ts
// lib/auth.ts
import { SignJWT, jwtVerify } from 'jose';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

export async function createSession(userId: number) {
  const token = await new SignJWT({ userId })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('14d')
    .sign(secret);
  
  cookies().set('session_token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 24 * 14, // 14 days
    path: '/',
  });
}
```

### 6.4 Email Template (Resend)

Use Resend free tier (3,000 emails/mo). From address: `onboarding@yourdomain.com` (verify domain in Resend dashboard, or use `resend.dev` for testing).

```ts
// lib/mail.ts
import { Resend } from 'resend';
const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendOTP(email: string, code: string) {
  await resend.emails.send({
    from: 'RC Prep <onboarding@yourdomain.com>',
    to: email,
    subject: 'Your RC Prep Login Code',
    html: `<p>Your verification code is: <strong>${code}</strong></p><p>Valid for 10 minutes.</p>`,
  });
}
```

---

## 7. Phase 4: Core Application UI

### 7.1 Theming (3 Modes)

Use CSS variables in `globals.css`, toggled via class on `<html>`:

```css
:root {
  --bg: #ffffff; --fg: #171717; --muted: #f5f5f4; --accent: #44403c;
}
.theme-reading {
  --bg: #fdf6e3; --fg: #433422; --muted: #f3e9d5; --accent: #8c6b4a;
}
.theme-dark {
  --bg: #1c1917; --fg: #e7e5e4; --muted: #292524; --accent: #a8a29e;
}
```

Components use `bg-[var(--bg)] text-[var(--fg)]`.

### 7.2 Passage Solving Screen (`/passage/[id]`)

**Desktop (≥1024px):**
- **Left 55%:** `passage-reader.tsx`
  - Scrollable container
  - Sticky toolbar: `A-` / `A` / `A+` font size buttons (14px / 16px / 18px / 20px / 22px)
  - Passage text with comfortable line-height (`leading-relaxed`)
- **Right 45%:** `question-card.tsx`
  - Shows current question number (e.g., "Question 2 of 5")
  - Options as radio cards (click to select)
  - Prev / Next buttons
  - "Submit Passage" button appears only on last question (or always visible but disabled until all answered)

**Mobile (<1024px):**
- **Top 50%:** Passage reader (scrollable, font controls)
- **Bottom 50%:** Question card (scrollable if needed)
- Use `flex-col h-[calc(100dvh-4rem)]` to occupy full viewport minus nav

**Timer:**
- Start when page loads (`useEffect` → `Date.now()`).
- Display `MM:SS` in top bar.
- On submit, send `total_time_seconds` to API.

**State Management (Client-side):**
```ts
// Store answers in a Map as user navigates
const [answers, setAnswers] = useState<<Record<number, string>>({}); // questionId -> option
```
- Auto-save to `localStorage` key `draft_passage_${passageId}` as backup.
- On submit, send full `answers` object to `POST /api/attempt/submit`.

### 7.3 Submit & Scoring Flow

1. User clicks **Submit** on last question (or a floating submit button).
2. Frontend confirms: "Are you sure? You have answered 4/5 questions."
3. `POST /api/attempt/submit` with `{ passageId, answers, timeSeconds }`.
4. Server:
   - Fetches correct options for the passage.
   - Compares `answers` → calculates `score`.
   - Inserts into `attempts` and `attempt_responses`.
   - Upserts `user_passage_status`:
     - `status = 'solved'`
     - `best_score = GREATEST(best_score, newScore)`
     - `best_time_seconds = LEAST(best_time_seconds, timeSeconds)` (lower is better)
     - `attempt_count += 1`
5. Redirects to `/passage/[id]/result`.

### 7.4 Result Screen (`/passage/[id]/result`)

- Score card: `You scored 4/5 (80%) in 8:24`
- List each question with:
  - Your answer (green if correct, red if wrong)
  - Correct answer
  - Explanation (if available; empty for now)
- Buttons: "Back to Dashboard", "Re-attempt Passage"

---

## 8. Phase 5: Dashboard & Progress Tracking

### 8.1 Dashboard (`/dashboard`)

**Stats Cards (top row):**
- **RCs Attempted:** `COUNT(DISTINCT passage_id)` from `attempts` where `user_id = ?`
- **Accuracy:** `SUM(score) / SUM(total_questions) * 100` across all completed attempts
- **Avg Time:** `AVG(total_time_seconds)` (format as `MM:SS`)
- **Current Streak:** Consecutive days with at least one completed attempt (calculated in SQL or API)

**Passage List (filterable):**
- Tabs: **All** | **Unsolved** | **Solved** | **Revision**
- Each card shows:
  - Source badge (GMAT-NEW, OG, etc.)
  - Passage #, Title (if any)
  - Status dot (unsolved = gray, solved = green, revision = blue)
  - If solved: Best score, Best time, Attempt count
- Sort: Sequential (default), or by "Most recently attempted"

**Weekly Activity Chart:**
- Query:
  ```sql
  SELECT DATE_TRUNC('week', completed_at) as week, COUNT(*) as count
  FROM attempts WHERE user_id = $1 AND is_completed = true
  GROUP BY week ORDER BY week DESC LIMIT 8;
  ```
- Render as simple HTML/CSS flex row of bars. No chart library needed.

### 8.2 API Endpoint

`GET /api/progress` returns:
```json
{
  "totalAttempted": 42,
  "totalPassages": 117,
  "accuracy": 68.5,
  "averageTimeSeconds": 540,
  "streakDays": 5,
  "weeklyData": [
    { "week": "2026-W19", "count": 7 },
    ...
  ],
  "passages": [
    { "id": 1, "source": "GMAT-NEW", "status": "solved", "bestScore": 5, "bestTime": 480, "attempts": 2 }
  ]
}
```

---

## 9. Phase 6: Deployment Checklist

### 9.1 Environment Variables (`.env.local`)

```bash
# Database
POSTGRES_URL="postgres://..."

# Auth
JWT_SECRET="random-32-char-string"
NEXT_PUBLIC_APP_URL="https://rc-prep.vercel.app"

# Email
RESEND_API_KEY="re_..."
RESEND_FROM_EMAIL="onboarding@yourdomain.com"
```

### 9.2 Vercel Config

- Install Vercel Postgres from the Vercel marketplace (free Hobby tier).
- Set all env vars in Project Settings.
- Ensure `middleware.ts` does not block public assets or auth routes.

### 9.3 Build & Seed

```bash
# 1. Local dev
npm run dev

# 2. Seed database (run once locally)
npx tsx scripts/seed/seed_db.ts

# 3. Deploy
vercel --prod
```

### 9.4 Post-Deployment (Adding a New PDF in Future)

When you get a new RC PDF:
1. Run the Python extraction pipeline (`01` → `02` → `03` → `04`) on the new PDF.
2. Review generated markdown files in `scripts/data/passings/`.
3. Run `npx tsx scripts/seed/seed_db.ts` against your production DB (or local first, then promote).
4. New passages appear instantly in the app with `id` auto-incrementing from 118 onwards.

---

## 10. Key Implementation Notes for the Coding Agent

1. **No repetition logic:** The dashboard query for "Unsolved" should filter where `user_passage_status.status != 'solved'`. The "All" tab shows everything but grays out solved ones. Clicking a solved one shows "Re-attempt" instead of "Start".

2. **Timer persistence:** If user refreshes the page mid-attempt, use `localStorage` to recover `startTime` and `answers`. On mount, check `localStorage` for `draft_passage_${id}` and restore.

3. **Mobile passage scrolling:** Use `overflow-y-auto` with `-webkit-overflow-scrolling: touch`. Font size buttons must increase/decrease a CSS variable `--passage-font-size` applied to the passage container.

4. **One question at a time:** Maintain `currentQuestionIndex` in React state. Prev/Next disabled at boundaries. Selected option visually highlighted immediately but only submitted to server at the end.

5. **Theme default:** Default to `theme-standard` (pure white). Save preference in `localStorage` + cookie to avoid hydration mismatch.

6. **PDF extraction is offline:** Do NOT add Python dependencies to the Next.js repo's `package.json`. Keep Python scripts in `scripts/extract/` with their own `requirements.txt` (`pdfplumber`, `python-frontmatter`).

7. **Security:**
   - Rate limit auth endpoints via Vercel KV or in-memory Map (sufficient for low traffic).
   - OTP codes expire in 10 minutes.
   - Passwords min 8 chars.

---
