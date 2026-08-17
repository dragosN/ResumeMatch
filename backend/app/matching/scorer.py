"""Weighted scoring from structured match results."""

from __future__ import annotations

from app.extraction.schemas import (
    CategoryScores,
    ExtractedProfile,
    ExtractedRequirements,
    SeniorityLevel,
)
from app.matching.normalize import canonical_skill
from app.matching.skill_matcher import MatchResult

SENIORITY_RANK = {
    SeniorityLevel.junior: 1,
    SeniorityLevel.mid: 2,
    SeniorityLevel.senior: 3,
    SeniorityLevel.lead: 4,
    SeniorityLevel.unknown: 0,
}

# Weights for overall score (must sum to 1.0)
WEIGHT_REQUIRED = 0.55
WEIGHT_EXPERIENCE = 0.20
WEIGHT_NICE = 0.15
WEIGHT_DOMAIN = 0.10


def compute_scores(
    match: MatchResult,
    profile: ExtractedProfile,
    requirements: ExtractedRequirements,
) -> tuple[float, CategoryScores]:
    """Return (overall_score, category_scores) from match result and extraction."""
    technical = _technical_score(match, requirements)
    experience = _experience_score(profile, requirements)
    domain = _domain_score(profile, requirements, match)
    soft = _soft_score(profile, requirements)

    overall = (
        WEIGHT_REQUIRED * technical
        + WEIGHT_EXPERIENCE * experience
        + WEIGHT_NICE * _nice_to_have_score(match, requirements)
        + WEIGHT_DOMAIN * domain
    )
    overall = round(min(100.0, max(0.0, overall)), 1)

    return overall, CategoryScores(
        technical=round(technical, 1),
        experience=round(experience, 1),
        domain=round(domain, 1),
        soft=round(soft, 1),
    )


def _required_jd_skills(requirements: ExtractedRequirements) -> set[str]:
    return {canonical_skill(s) for s in requirements.required_skills}


def _technical_score(match: MatchResult, requirements: ExtractedRequirements) -> float:
    required_total = len(requirements.required_skills)
    if required_total == 0:
        return 100.0
    req_canon = _required_jd_skills(requirements)
    matched = sum(1 for m in match.matched_skills if canonical_skill(m.jd_skill) in req_canon)
    # Review-band required skills count as partial credit (50%)
    review_required = sum(
        1 for r in match.review_band if canonical_skill(r.jd_skill) in req_canon
    )
    credit = matched + 0.5 * review_required
    return min(100.0, 100.0 * credit / required_total)


def _nice_to_have_score(match: MatchResult, requirements: ExtractedRequirements) -> float:
    total = len(requirements.nice_to_have_skills)
    if total == 0:
        return 100.0
    matched_nice = sum(
        1
        for m in match.matched_skills
        if m.jd_skill in requirements.nice_to_have_skills
    )
    review_nice = sum(
        1 for r in match.review_band if r.jd_skill in requirements.nice_to_have_skills
    )
    credit = matched_nice + 0.5 * review_nice
    return min(100.0, 100.0 * credit / total)


def _experience_score(profile: ExtractedProfile, requirements: ExtractedRequirements) -> float:
    parts: list[float] = []

    if requirements.min_years_experience is not None and profile.years_experience is not None:
        required = requirements.min_years_experience
        actual = profile.years_experience
        if actual >= required:
            parts.append(100.0)
        elif required > 0:
            parts.append(max(0.0, 100.0 * actual / required))
        else:
            parts.append(50.0)
    elif profile.years_experience is not None:
        parts.append(70.0)
    else:
        parts.append(50.0)

    if requirements.seniority_level and profile.seniority_level:
        req_rank = SENIORITY_RANK.get(requirements.seniority_level, 0)
        prof_rank = SENIORITY_RANK.get(profile.seniority_level, 0)
        if req_rank == 0 or prof_rank == 0:
            parts.append(50.0)
        elif prof_rank == req_rank:
            parts.append(100.0)
        elif prof_rank > req_rank:
            parts.append(85.0)  # slightly overqualified is still good
        else:
            gap = req_rank - prof_rank
            parts.append(max(0.0, 100.0 - gap * 25.0))
    else:
        parts.append(50.0)

    return sum(parts) / len(parts)


def _domain_score(
    profile: ExtractedProfile,
    requirements: ExtractedRequirements,
    match: MatchResult,
) -> float:
    """Rough domain overlap via role titles and matched JD skills."""
    if not requirements.responsibilities and not requirements.required_skills:
        return 50.0

    profile_tokens = _token_set(profile.roles + profile.skills)
    req_tokens = _token_set(requirements.responsibilities + requirements.required_skills)
    if not req_tokens:
        return 50.0
    overlap = len(profile_tokens & req_tokens) / len(req_tokens)
    matched_ratio = len(match.matched_skills) / max(len(requirements.required_skills), 1)
    return min(100.0, 100.0 * (0.4 * overlap + 0.6 * matched_ratio))


def _soft_score(profile: ExtractedProfile, requirements: ExtractedRequirements) -> float:
    soft_keywords = {
        "communication",
        "leadership",
        "team",
        "collaboration",
        "mentoring",
        "stakeholder",
        "agile",
        "scrum",
    }
    profile_text = " ".join(profile.roles + profile.skills + [profile.summary]).lower()
    req_text = " ".join(requirements.responsibilities).lower()
    if not req_text:
        return 60.0
    hits = sum(1 for kw in soft_keywords if kw in req_text and kw in profile_text)
    req_hits = sum(1 for kw in soft_keywords if kw in req_text)
    if req_hits == 0:
        return 60.0
    return min(100.0, 100.0 * hits / req_hits)


def _token_set(items: list[str]) -> set[str]:
    tokens: set[str] = set()
    for item in items:
        for part in canonical_skill(item).replace("/", " ").split():
            if len(part) > 2:
                tokens.add(part)
    return tokens
