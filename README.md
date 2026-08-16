# ResumeMatch

Resume ↔ Job Description gap analyzer. Next.js frontend + FastAPI backend.
Ollama-first LLM/embeddings with a pluggable provider seam for Claude/etc. later.

## Day 1 status

- Scaffold, CORS, health, mirrored Pydantic/Zod schemas
- PDF/DOCX/URL ingest
- LLM structured extraction (resume + JD) with validation retry
- `/analyze` live extraction + stub matching; `/analyze/stub` for UI without Ollama
- Frontend upload/paste UI with up to 3 JD slots (compare on Day 3)

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

## Provider swap

`LLM_PROVIDER` / `EMBEDDING_PROVIDER` default to `ollama`. Call sites use
`get_chat_provider()` / `get_embedding_provider()` only. To add Claude later:
implement adapters under `backend/app/llm/` and register them in
`provider.py` — no changes to extraction code.
