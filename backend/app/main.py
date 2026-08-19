"""FastAPI entrypoint for ResumeMatch."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.extraction.analyze import (
    analyze_texts,
    compare_texts,
    stub_analyze_response,
    stub_compare_response,
)
from app.extraction.schemas import AnalyzeResponse, CompareResponse
from app.ingest.documents import extract_text_from_upload, resolve_jd_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ResumeMatch", version="0.3.0")

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
    """Analyze resume vs one JD."""
    if settings.analyze_stub:
        return stub_analyze_response()

    try:
        r_text = await _load_resume_text(resume, resume_text)
        j_text = await _resolve_single_jd(jd_text, jd_url, jd_file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        raise HTTPException(status_code=400, detail=f"Failed to read documents: {exc}") from exc

    _validate_text_lengths(r_text, j_text)

    try:
        return analyze_texts(r_text, j_text)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analyze failed")
        raise HTTPException(
            status_code=502,
            detail=f"Analysis failed (is Ollama running?): {exc}",
        ) from exc


@app.post("/analyze/compare", response_model=CompareResponse)
async def analyze_compare(
    resume: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    jd_text_0: Optional[str] = Form(None),
    jd_url_0: Optional[str] = Form(None),
    jd_file_0: Optional[UploadFile] = File(None),
    jd_text_1: Optional[str] = Form(None),
    jd_url_1: Optional[str] = Form(None),
    jd_file_1: Optional[UploadFile] = File(None),
    jd_text_2: Optional[str] = Form(None),
    jd_url_2: Optional[str] = Form(None),
    jd_file_2: Optional[UploadFile] = File(None),
    jd_label_0: Optional[str] = Form(None),
    jd_label_1: Optional[str] = Form(None),
    jd_label_2: Optional[str] = Form(None),
) -> CompareResponse:
    """Compare one resume against up to 3 job descriptions; returns ranked results."""
    if settings.analyze_stub:
        return stub_compare_response()

    slots = [
        (jd_text_0, jd_url_0, jd_file_0, jd_label_0),
        (jd_text_1, jd_url_1, jd_file_1, jd_label_1),
        (jd_text_2, jd_url_2, jd_file_2, jd_label_2),
    ]

    try:
        r_text = await _load_resume_text(resume, resume_text)
        jd_texts: list[str] = []
        labels: list[str] = []
        for idx, (text, url, file, label) in enumerate(slots):
            if not _slot_has_input(text, url, file):
                continue
            j_text = await _resolve_single_jd(text, url, file)
            if len(j_text.strip()) < 40:
                raise ValueError(f"Job description slot {idx + 1} is too short.")
            jd_texts.append(j_text)
            labels.append(label.strip() if label and label.strip() else "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Compare ingest failed")
        raise HTTPException(status_code=400, detail=f"Failed to read documents: {exc}") from exc

    if not jd_texts:
        raise HTTPException(status_code=400, detail="Provide at least one job description.")
    if len(r_text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Resume text is too short.")

    clean_labels = [lbl or "" for lbl in labels]
    try:
        return compare_texts(r_text, jd_texts, labels=clean_labels)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Compare failed")
        raise HTTPException(
            status_code=502,
            detail=f"Compare failed (is Ollama running?): {exc}",
        ) from exc


@app.post("/analyze/stub", response_model=AnalyzeResponse)
def analyze_stub() -> AnalyzeResponse:
    """Always return hardcoded JSON — useful for frontend UI work without Ollama."""
    return stub_analyze_response()


@app.post("/analyze/compare/stub", response_model=CompareResponse)
def analyze_compare_stub() -> CompareResponse:
    """Hardcoded multi-JD compare response."""
    return stub_compare_response()


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


async def _resolve_single_jd(
    jd_text: Optional[str],
    jd_url: Optional[str],
    jd_file: Optional[UploadFile],
) -> str:
    j_bytes: Optional[bytes] = None
    j_name: Optional[str] = None
    if jd_file is not None and jd_file.filename:
        j_bytes = await jd_file.read()
        j_name = jd_file.filename
    return resolve_jd_text(
        jd_text=jd_text,
        jd_url=jd_url,
        jd_filename=j_name,
        jd_bytes=j_bytes,
    )


def _slot_has_input(
    jd_text: Optional[str],
    jd_url: Optional[str],
    jd_file: Optional[UploadFile],
) -> bool:
    if jd_text and jd_text.strip():
        return True
    if jd_url and jd_url.strip():
        return True
    if jd_file is not None and jd_file.filename:
        return True
    return False


def _validate_text_lengths(resume_text: str, jd_text: str) -> None:
    if len(resume_text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Resume text is too short.")
    if len(jd_text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Job description text is too short.")
