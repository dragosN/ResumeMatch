"""FastAPI entrypoint for ResumeMatch."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.extraction.analyze import analyze_texts, stub_analyze_response
from app.extraction.schemas import AnalyzeResponse
from app.ingest.documents import extract_text_from_upload, resolve_jd_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ResumeMatch", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "analyze_stub": settings.analyze_stub,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    resume: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    jd_url: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
) -> AnalyzeResponse:
    """Analyze resume vs one JD. Extraction + layered matching unless ANALYZE_STUB."""
    if settings.analyze_stub:
        return stub_analyze_response()

    try:
        r_text = await _load_resume_text(resume, resume_text)
        j_bytes: Optional[bytes] = None
        j_name: Optional[str] = None
        if jd_file is not None:
            j_bytes = await jd_file.read()
            j_name = jd_file.filename or "jd.txt"
        j_text = resolve_jd_text(
            jd_text=jd_text,
            jd_url=jd_url,
            jd_filename=j_name,
            jd_bytes=j_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        raise HTTPException(status_code=400, detail=f"Failed to read documents: {exc}") from exc

    if len(r_text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Resume text is too short.")
    if len(j_text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Job description text is too short.")

    try:
        return analyze_texts(r_text, j_text)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analyze failed")
        raise HTTPException(
            status_code=502,
            detail=f"Extraction failed (is Ollama running?): {exc}",
        ) from exc


@app.post("/analyze/stub", response_model=AnalyzeResponse)
def analyze_stub() -> AnalyzeResponse:
    """Always return hardcoded JSON — useful for frontend UI work without Ollama."""
    return stub_analyze_response()


async def _load_resume_text(
    resume: Optional[UploadFile],
    resume_text: Optional[str],
) -> str:
    if resume is not None and resume.filename:
        data = await resume.read()
        if data:
            return extract_text_from_upload(resume.filename, data)
    if resume_text and resume_text.strip():
        return resume_text.strip()
    raise ValueError("Provide a resume file (PDF/DOCX) or resume_text.")
