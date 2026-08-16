"""Resume → ExtractedProfile via LLM structured JSON + Pydantic validation retry."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.extraction.schemas import ExtractedProfile, SeniorityLevel
from app.llm.provider import ChatProvider

PROFILE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "skills": {"type": "array", "items": {"type": "string"}},
        "years_experience": {"type": ["number", "null"]},
        "seniority_level": {
            "type": ["string", "null"],
            "enum": ["junior", "mid", "senior", "lead", "unknown", None],
        },
        "roles": {"type": "array", "items": {"type": "string"}},
        "education": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["skills", "roles", "education", "summary"],
}

SYSTEM_PROMPT = """You extract structured career data from resume text.
Return only JSON matching the schema. Be thorough on skills — include languages,
frameworks, tools, cloud, databases, and soft skills explicitly named.
Infer years_experience as a single float when possible (total professional experience).
seniority_level must be one of: junior, mid, senior, lead, unknown.
If a field is truly absent, use null or []. Do not invent employers or degrees.

Few-shot examples:

Example A (prose-style resume excerpt):
INPUT:
"Alex Chen is a software engineer with five years building React and Node services
for fintech. Previously a junior developer at Acme. B.S. Computer Science, State U."
OUTPUT:
{
  "skills": ["React", "Node", "fintech"],
  "years_experience": 5.0,
  "seniority_level": "mid",
  "roles": ["software engineer", "junior developer"],
  "education": ["B.S. Computer Science, State U"],
  "summary": "Software engineer with 5 years in React/Node fintech."
}

Example B (list/table-style resume excerpt):
INPUT:
"SKILLS: Python | Django | PostgreSQL | AWS
EXPERIENCE: Senior Backend Engineer, Globex (2018–2024) — 6 years
EDUCATION: M.S. Software Engineering"
OUTPUT:
{
  "skills": ["Python", "Django", "PostgreSQL", "AWS"],
  "years_experience": 6.0,
  "seniority_level": "senior",
  "roles": ["Senior Backend Engineer"],
  "education": ["M.S. Software Engineering"],
  "summary": "Senior backend engineer, 6 years, Python/Django/AWS."
}
"""


def _completeness_warnings(profile: ExtractedProfile, raw_text: str) -> list[str]:
    warnings: list[str] = []
    nontrivial = len(raw_text.strip()) > 200
    if nontrivial and not profile.skills:
        warnings.append(
            "skills_empty: resume text looks substantial but no skills were extracted — "
            "possible extraction failure, not an empty resume."
        )
    if nontrivial and profile.years_experience is None:
        warnings.append(
            "years_experience_null: could not infer years of experience; treat as incomplete extraction."
        )
    return warnings


def _coerce_seniority(value: Any) -> SeniorityLevel | None:
    if value is None or value == "":
        return None
    try:
        return SeniorityLevel(str(value).lower())
    except ValueError:
        return SeniorityLevel.unknown


def parse_resume(text: str, chat: ChatProvider) -> ExtractedProfile:
    user = f"Extract a structured profile from this resume:\n\n{text[:20000]}"
    data = chat.complete_json(SYSTEM_PROMPT, user, PROFILE_JSON_SCHEMA)
    try:
        profile = _to_profile(data)
    except ValidationError as first_err:
        retry_user = (
            f"{user}\n\nYour previous JSON failed validation:\n{first_err}\n"
            "Return corrected JSON only."
        )
        data = chat.complete_json(SYSTEM_PROMPT, retry_user, PROFILE_JSON_SCHEMA)
        profile = _to_profile(data)

    profile.extraction_warnings = _completeness_warnings(profile, text)
    return profile


def _to_profile(data: dict[str, Any]) -> ExtractedProfile:
    payload = {
        "skills": data.get("skills") or [],
        "years_experience": data.get("years_experience"),
        "seniority_level": _coerce_seniority(data.get("seniority_level")),
        "roles": data.get("roles") or [],
        "education": data.get("education") or [],
        "summary": data.get("summary") or "",
    }
    return ExtractedProfile.model_validate(payload)
