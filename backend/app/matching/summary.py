"""Grounded LLM summary from structured match/score data only."""

from __future__ import annotations

import json
from typing import Any

from app.extraction.schemas import (
    CategoryScores,
    ExtractedProfile,
    ExtractedRequirements,
)
from app.llm.provider import ChatProvider
from app.matching.skill_matcher import MatchResult

SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "2-4 sentence plain-English assessment grounded in the structured data",
        }
    },
    "required": ["summary"],
}

SYSTEM = """You write concise, honest resume-vs-job match assessments for candidates.
You receive ONLY pre-computed structured data (scores, matched skills, gaps). Do not invent
skills or gaps not present in the data. Name specific missing required skills when listed.
Tone: direct, helpful, like a senior recruiter giving candid feedback. 2-4 sentences max."""


def generate_summary(
    match: MatchResult,
    overall_score: float,
    category_scores: CategoryScores,
    profile: ExtractedProfile,
    requirements: ExtractedRequirements,
    chat: ChatProvider,
) -> str:
    """Generate a grounded summary paragraph from structured analysis data."""
    payload = {
        "overall_score": overall_score,
        "category_scores": category_scores.model_dump(),
        "matched_skills": [
            {
                "resume": m.resume_skill,
                "requirement": m.jd_skill,
                "reason": m.reason,
            }
            for m in match.matched_skills
        ],
        "missing_required": [m.jd_skill for m in match.missing_required],
        "missing_nice_to_have": [m.jd_skill for m in match.missing_nice_to_have],
        "review_band": [
            {"resume": r.resume_skill, "requirement": r.jd_skill, "reason": r.reason}
            for r in match.review_band
        ],
        "overqualified": match.overqualified,
        "candidate_years": profile.years_experience,
        "candidate_seniority": profile.seniority_level,
        "required_years": requirements.min_years_experience,
        "required_seniority": requirements.seniority_level,
    }
    user = (
        "Write a match assessment using ONLY this structured data:\n\n"
        f"{json.dumps(payload, indent=2)}"
    )
    try:
        result = chat.complete_json(SYSTEM, user, SUMMARY_SCHEMA)
        summary = str(result.get("summary", "")).strip()
        if summary:
            return summary
    except Exception:  # noqa: BLE001
        pass
    return _fallback_summary(match, overall_score)


def _fallback_summary(match: MatchResult, overall_score: float) -> str:
    """Deterministic summary when LLM is unavailable."""
    parts = [f"Overall match score: {overall_score}/100."]
    if match.matched_skills:
        names = ", ".join(m.jd_skill for m in match.matched_skills[:6])
        parts.append(f"Strong overlap on: {names}.")
    if match.missing_required:
        gaps = ", ".join(m.jd_skill for m in match.missing_required)
        parts.append(f"Missing required skills: {gaps}.")
    if match.review_band:
        parts.append(
            f"{len(match.review_band)} skill pair(s) need manual review (possible semantic matches)."
        )
    return " ".join(parts)
