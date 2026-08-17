# ResumeMatch

Resume ↔ Job Description gap analyzer. Next.js frontend + FastAPI backend.
Ollama-first LLM/embeddings with a pluggable provider seam for Claude/etc. later.

## Day 2 status

- Layered skill matcher: normalize → synonyms → embeddings → confusables → LLM arbiter
- Weighted scoring (required / experience / nice-to-have / domain) with category breakdown
- Grounded LLM summary from structured match data (not raw documents)
- Labeled eval set (`backend/eval/skill_pairs.jsonl`, 30 pairs) + precision/recall script
- Unit tests for normalization, confusables, thresholds, scoring sanity checks

## Day 1 status

- Scaffold, CORS, health, mirrored Pydantic/Zod schemas
- PDF/DOCX/URL ingest
- LLM structured extraction (resume + JD) with validation retry
- `/analyze` live extraction + semantic matching; `/analyze/stub` for UI without Ollama
- Frontend upload/paste UI with up to 3 JD slots (compare on Day 3)

## Matching pipeline

1. **Normalize** — lowercase, collapse `.js` suffixes, synonym map (`react.js`→`react`, `js`→`javascript`, `html5`→`html`)
2. **Implications** — TypeScript covers JavaScript (not the reverse); CSS/HTML cover each other; Sass/Tailwind cover CSS; React/Next.js cover JavaScript
3. **Embed** — Ollama `nomic-embed-text`; cosine similarity between resume and JD skills
4. **Thresholds** — match ≥0.85, review 0.65–0.85 (tunable via `MATCH_THRESHOLD` / `REVIEW_THRESHOLD`)
5. **Confusables** — `java`↔`javascript`, `aws`↔`azure`, etc. never auto-match on embedding alone
6. **LLM arbiter** — review-band pairs only; targeted yes/no grounded prompt

Run eval against Ollama embeddings:

```bash
cd backend && source .venv/bin/activate
PYTHONPATH=. python eval/run_eval.py
```

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Ensure Ollama is running with chat + embed models:
#   ollama pull llama3.1:8b
#   ollama pull nomic-embed-text
uvicorn app.main:app --reload --port 8000
```

Default chat model is `llama3.1:8b` (override via `OLLAMA_CHAT_MODEL`).
Set `ANALYZE_STUB=true` in `.env` to skip Ollama entirely.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — check “Use stub response” to render without the LLM.

### Tests

```bash
cd backend && source .venv/bin/activate
PYTHONPATH=. pytest -q
```

## Provider swap

`LLM_PROVIDER` / `EMBEDDING_PROVIDER` default to `ollama`. Call sites use
`get_chat_provider()` / `get_embedding_provider()` only. To add Claude later:
implement adapters under `backend/app/llm/` and register them in
`provider.py` — no changes to extraction or matching code.
