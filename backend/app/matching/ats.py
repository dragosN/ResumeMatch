"""ATS keyword check — literal phrase scan of resume text vs JD phrases."""

from __future__ import annotations

import re

from app.extraction.schemas import AtsFlag, ExtractedRequirements


def check_ats_phrases(resume_text: str, requirements: ExtractedRequirements) -> list[AtsFlag]:
    """Flag whether each JD ATS phrase appears literally in the resume."""
    phrases = _dedupe_phrases(requirements.ats_phrases or [])
    if not phrases:
        phrases = _dedupe_phrases(
            requirements.required_skills + requirements.nice_to_have_skills
        )
    haystack = resume_text.lower()
    return [
        AtsFlag(phrase=phrase, found_in_resume=_phrase_in_text(phrase, haystack))
        for phrase in phrases
    ]


def _dedupe_phrases(phrases: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in phrases:
        key = p.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(p.strip())
    return out


def _phrase_in_text(phrase: str, haystack_lower: str) -> bool:
    needle = phrase.strip().lower()
    if not needle:
        return False
    if needle in haystack_lower:
        return True
    # Allow hyphen/space variants: "ci/cd" vs "ci cd"
    alt = re.sub(r"[\s\-_/]+", " ", needle)
    if alt != needle and alt in haystack_lower:
        return True
    # Word-boundary match for short tokens to reduce false positives
    if len(needle) <= 4:
        return bool(re.search(rf"\b{re.escape(needle)}\b", haystack_lower))
    return False
