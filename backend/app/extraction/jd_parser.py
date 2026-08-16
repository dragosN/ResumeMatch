"""Job description → ExtractedRequirements via LLM structured JSON + retry."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.extraction.schemas import ExtractedRequirements, SeniorityLevel
from app.llm.provider import ChatProvider

REQUIREMENTS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "nice_to_have_skills": {"type": "array", "items": {"type": "string"}},
        "min_years_experience": {"type": ["number", "null"]},
        "seniority_level": {
            "type": ["string", "null"],
            "enum": ["junior", "mid", "senior", "lead", "unknown", None],
        },
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "ats_phrases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exact skill/tool phrases an ATS might scan for literally",
        },
    },
    "required": ["required_skills", "nice_to_have_skills", "responsibilities", "ats_phrases"],
}

SYSTEM_PROMPT = """You extract hiring requirements from a job description.
Return only JSON matching the schema.
Split must-have skills into required_skills and optional ones into nice_to_have_skills.
ats_phrases: short exact phrases (technologies, certifications, titles) that applicant
tracking systems often match literally — prefer the JD's own wording.
seniority_level must be one of: junior, mid, senior, lead, unknown.
Do not invent requirements that are not implied by the text.

Few-shot:

INPUT:
"We need a Senior React engineer (5+ years). Must know TypeScript and GraphQL.
Nice to have: Next.js, experience with design systems. Own the frontend roadmap."
OUTPUT:
{
  "required_skills": ["React", "TypeScript", "GraphQL"],
  "nice_to_have_skills": ["Next.js", "design systems"],
  "min_years_experience": 5.0,
  "seniority_level": "senior",
  "responsibilities": ["Own the frontend roadmap"],
  "ats_phrases": ["React", "TypeScript", "GraphQL", "Next.js", "Senior"]
}
"""


def _coerce_seniority(value: Any) -> SeniorityLevel | None:
    if value is None or value == "":
        return None
    try:
        return SeniorityLevel(str(value).lower())
    except ValueError:
        return SeniorityLevel.unknown


def _completeness_warnings(req: ExtractedRequirements, raw_text: str) -> list[str]:
    warnings: list[str] = []
    nontrivial = len(raw_text.strip()) > 150
    if nontrivial and not req.required_skills and not req.nice_to_have_skills:
        warnings.append(
            "skills_empty: JD text looks substantial but no skills were extracted."
        )
    return warnings


def parse_jd(text: str, chat: ChatProvider) -> ExtractedRequirements:
    user = f"Extract structured requirements from this job description:\n\n{text[:20000]}"
    data = chat.complete_json(SYSTEM_PROMPT, user, REQUIREMENTS_JSON_SCHEMA)
    try:
        req = _to_requirements(data)
    except ValidationError as first_err:
        retry_user = (
            f"{user}\n\nYour previous JSON failed validation:\n{first_err}\n"
            "Return corrected JSON only."
        )
        data = chat.complete_json(SYSTEM_PROMPT, retry_user, REQUIREMENTS_JSON_SCHEMA)
        req = _to_requirements(data)

    # Ensure ats_phrases has at least required + nice-to-have if model left it empty
    if not req.ats_phrases:
        req.ats_phrases = list(
            dict.fromkeys([*req.required_skills, *req.nice_to_have_skills])
        )

    req.extraction_warnings = _completeness_warnings(req, text)
    return req


def _to_requirements(data: dict[str, Any]) -> ExtractedRequirements:
    payload = {
        "required_skills": data.get("required_skills") or [],
        "nice_to_have_skills": data.get("nice_to_have_skills") or [],
        "min_years_experience": data.get("min_years_experience"),
        "seniority_level": _coerce_seniority(data.get("seniority_level")),
        "responsibilities": data.get("responsibilities") or [],
        "ats_phrases": data.get("ats_phrases") or [],
    }
    return ExtractedRequirements.model_validate(payload)
