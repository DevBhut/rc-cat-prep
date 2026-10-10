# AGENTS.md — RC CAT Prep

## What this repo is

A **Next.js 15 full-stack application** for CAT Reading Comprehension practice, plus a Python offline pipeline for extracting passages from a 1000-page PDF.

- `Prompts/initial_planning.md` — The canonical 886-line implementation plan. Read this first before any implementation work.
- `PDFS/1000_RC.pdf` — Source material (not tracked in git).

## Package managers

- **JavaScript/TypeScript:** `bun` (not npm). Lockfile is `bun.lock`.
  - Install deps: `bun install`
  - Add dep: `bun add <pkg>`
  - Dev server: `bun run dev` (uses `--turbopack`)
  - Run TS scripts: `bun run <script.ts>` (bun executes TypeScript natively; no `tsx` needed)
- **Python:** `uv` (not pip).
  - The Python project is at `scripts/extract/` with its own `pyproject.toml`.
  - Run scripts: `cd scripts/extract && uv run <script.py>`
  - Add deps: `cd scripts/extract && uv add <pkg>`

## Key commands

1. **Dev server:** `bun run dev`
2. **Lint:** `bun run lint`
3. **Format:** `bun run format`
4. **Typecheck:** `bun run typecheck`
5. **Seed DB:** `bun run scripts/seed/seed_db.ts`
6. **Extract PDF (pipeline):**
   ```bash
   cd scripts/extract
   uv run 01_extract_raw.py
   uv run 02_slice_passages.py
   uv run 03_extract_solutions.py
   uv run 04_llm_validate.py   # optional
   uv run 05_generate_markdown.py
   ```

## Tech stack

- Next.js 15 (App Router) + TypeScript
- Vercel Postgres (`@vercel/postgres`) + raw SQL (`scripts/seed/schema.sql`)
- Tailwind CSS v4 + shadcn/ui (`neutral` base color — **note:** the plan specifies `stone` for warm paper-like theme, but the current init uses `neutral`. Update in `components.json` and `globals.css` if implementing the reading theme.)
- Custom JWT auth (`jose` + `bcryptjs`) with Resend OTP email
- Python offline extraction (`pdfplumber`, `PyMuPDF`, `python-frontmatter`)

## Project structure

```
├── app/               # Next.js App Router
│   ├── (auth)/      # login, signup, verify-otp (directories exist, pages empty)
│   ├── (app)/         # dashboard, passage/[id], layout (directories exist, pages empty)
│   └── api/           # auth, passage, attempt, progress routes (directories exist, handlers empty)
├── components/        # React components (shadcn/ui + custom)
│   ├── ui/            # shadcn/ui components (only button.tsx exists)
│   └── theme-provider.tsx  # next-themes provider with dark/light toggle via 'd' hotkey
├── lib/               # db.ts, auth.ts, password.ts, otp.ts, mail.ts, utils.ts
├── scripts/
│   ├── extract/       # Python pipeline (uv project) — scripts are stubs
│   └── seed/          # schema.sql, seed_db.ts — seed script is a stub
├── middleware.ts      # JWT route protection (stub)
├── PDFS/              # 1000_RC.pdf (not in git)
└── Prompts/           # initial_planning.md
```

## Environment variables

Copy `.env.local` and fill in:
- `POSTGRES_URL` — Vercel Postgres connection string
- `JWT_SECRET` — random 32+ char string
- `NEXT_PUBLIC_APP_URL` — `http://localhost:3000` for dev
- `RESEND_API_KEY` + `RESEND_FROM_EMAIL` — for OTP emails

## What exists vs. what needs building

**Exists:**
- Next.js 15 scaffold with bun, Tailwind v4, shadcn/ui (neutral base)
- Database schema (`scripts/seed/schema.sql`)
- Auth lib helpers (`lib/auth.ts`, `lib/password.ts`, `lib/otp.ts`, `lib/mail.ts`)
- DB client setup (`lib/db.ts`)
- Middleware stub (`middleware.ts`)
- Python project with dependencies installed (`scripts/extract/`)
- Theme provider with next-themes (dark/light toggle only)

**Needs implementation:**
- All API routes (`app/api/*`) — directories created, route handlers empty
- All pages (`app/(auth)/*`, `app/(app)/*`) — directories created, page files empty
- All custom UI components (`components/*`) — only theme-provider.tsx and ui/button.tsx exist
- Python extraction pipeline logic (scripts are stubs)
- Seed script implementation
- Three-mode theme system (standard/reading/dark) — currently only dark/light via next-themes

## Theming

**Current state:** Only dark/light mode via `next-themes` with a 'd' hotkey toggle. CSS variables in `globals.css` use standard shadcn `neutral` colors.

**Planned (from spec):** Three modes: standard (white), reading (warm beige `#fdf6e3`), dark. The plan specifies `stone` as the Tailwind base color and custom CSS variables `--bg`, `--fg`, `--muted`, `--accent`. If implementing the reading theme, update `components.json` baseColor to `stone` and rewrite `globals.css` with the custom variable scheme.

## Git

- **Do NOT commit** `PDFS/1000_RC.pdf`, `.env.local`, or extracted data images.
- `.gitignore` already excludes `node_modules`, `.next`, Python artifacts, and `scripts/data/passages/**/pages/`.
- GitHub repo: `https://github.com/DevBhut/rc-cat-prep`
