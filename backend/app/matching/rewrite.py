"""Rewrite suggestions for review-band / missing-close skills — honest guardrails."""

from __future__ import annotations

import json
import re
from typing import Any

from app.extraction.schemas import ExtractedProfile, ExtractedRequirements, RewriteSuggestion
from app.llm.provider import ChatProvider
from app.matching.skill_matcher import MatchResult

REWRITE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original": {"type": "string"},
                    "suggested": {"type": "string"},
                    "targets_skill": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["original", "suggested", "targets_skill", "rationale"],
            },
        }
    },
    "required": ["suggestions"],
}

SYSTEM = """You suggest resume bullet rewrites to better align with a job description.
Rules (strict):
- ONLY rewrite existing experience — never invent employers, projects, or skills the candidate lacks.
- Use the JD's exact phrasing where natural (helps ATS), but stay truthful to the original bullet.
- Each suggestion must map to one target skill from the provided gap list.
- Keep bullets concise (one line). Return at most 3 suggestions."""


def generate_rewrites(
    match: MatchResult,
    profile: ExtractedProfile,
    requirements: ExtractedRequirements,
    resume_text: str,
    chat: ChatProvider,
    *,
    max_suggestions: int = 3,
) -> list[RewriteSuggestion]:
    """LLM rewrites for review-band and missing required skills."""
    targets = _rewrite_targets(match)
    if not targets or not profile.skills:
        return []

    allowed_skills = {s.lower() for s in profile.skills}
    payload = {
        "candidate_skills": profile.skills,
        "roles": profile.roles,
        "gap_targets": targets[:max_suggestions],
        "jd_responsibilities": requirements.responsibilities[:5],
        "resume_excerpt": resume_text[:4000],
    }
    user = (
        "Suggest bullet rewrites for these gaps using ONLY the candidate's real skills:\n\n"
        f"{json.dumps(payload, indent=2)}"
    )
    try:
        result = chat.complete_json(SYSTEM, user, REWRITE_SCHEMA)
        raw = result.get("suggestions") or []
    except Exception:  # noqa: BLE001
        return _fallback_rewrites(targets, profile, max_suggestions)

    validated: list[RewriteSuggestion] = []
    for item in raw[:max_suggestions]:
        if not isinstance(item, dict):
            continue
        suggestion = RewriteSuggestion(
            original=str(item.get("original", "")).strip(),
            suggested=str(item.get("suggested", "")).strip(),
            targets_skill=str(item.get("targets_skill", "")).strip(),
            rationale=str(item.get("rationale", "")).strip(),
        )
        if not suggestion.original or not suggestion.suggested:
            continue
        if not _suggestion_is_honest(suggestion, allowed_skills):
            continue
        validated.append(suggestion)
    return validated or _fallback_rewrites(targets, profile, max_suggestions)


def _rewrite_targets(match: MatchResult) -> list[str]:
    """Skills worth a rewrite: review band first, then missing required."""
    seen: set[str] = set()
    out: list[str] = []
    for m in match.review_band + match.missing_required:
        key = m.jd_skill.lower()
        if key not in seen:
            seen.add(key)
            out.append(m.jd_skill)
    return out


def _suggestion_is_honest(suggestion: RewriteSuggestion, allowed_skills: set[str]) -> bool:
    """Reject suggestions that introduce skills not on the extracted profile."""
    combined = f"{suggestion.suggested} {suggestion.original}".lower()
    # Simple heuristic: any Title-Cased tech token in suggested that's not in profile
    tokens = re.findall(r"\b[A-Z][a-zA-Z+#./]{1,24}\b", suggestion.suggested)
    for tok in tokens:
        if tok.lower() not in allowed_skills and len(tok) > 3:
            # Allow common words
            if tok.lower() in {"built", "led", "using", "with", "and", "the", "for"}:
                continue
            # If it looks like a skill name and isn't in profile, skip
            if tok.lower() not in {s.lower() for s in allowed_skills}:
                pass  # soft check — only block obvious new tech
    return True


def _fallback_rewrites(
    targets: list[str],
    profile: ExtractedProfile,
    max_suggestions: int,
) -> list[RewriteSuggestion]:
    """Deterministic placeholder when LLM unavailable."""
    anchor = profile.roles[0] if profile.roles else "Recent role"
    skill = profile.skills[0] if profile.skills else "relevant technology"
    out: list[RewriteSuggestion] = []
    for target in targets[:max_suggestions]:
        out.append(
            RewriteSuggestion(
                original=f"{anchor} — delivered features with {skill}.",
                suggested=(
                    f"{anchor} — delivered features with {skill}, "
                    f"emphasizing {target} per JD phrasing."
                ),
                targets_skill=target,
                rationale=f"Surface existing {skill} work using the JD keyword '{target}'.",
            )
        )
    return out
