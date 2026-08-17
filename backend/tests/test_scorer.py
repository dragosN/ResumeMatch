from app.extraction.schemas import (
    ExtractedProfile,
    ExtractedRequirements,
    MatchConfidence,
    SeniorityLevel,
    SkillMatch,
)
from app.matching.scorer import compute_scores
from app.matching.skill_matcher import MatchResult


def _base_profile(**kwargs) -> ExtractedProfile:
    defaults = dict(
        skills=["React", "TypeScript", "Node"],
        years_experience=5.0,
        seniority_level=SeniorityLevel.mid,
        roles=["Frontend Engineer"],
        education=[],
        summary="",
    )
    defaults.update(kwargs)
    return ExtractedProfile(**defaults)


def _base_requirements(**kwargs) -> ExtractedRequirements:
    defaults = dict(
        required_skills=["React", "TypeScript", "GraphQL"],
        nice_to_have_skills=["Next.js"],
        min_years_experience=4.0,
        seniority_level=SeniorityLevel.mid,
        responsibilities=["Build UI"],
        ats_phrases=[],
    )
    defaults.update(kwargs)
    return ExtractedRequirements(**defaults)


def test_score_drops_when_required_skill_removed():
    full_match = MatchResult(
        matched_skills=[
            SkillMatch(resume_skill="React", jd_skill="React", confidence=MatchConfidence.matched),
            SkillMatch(resume_skill="TypeScript", jd_skill="TypeScript", confidence=MatchConfidence.matched),
            SkillMatch(resume_skill="GraphQL", jd_skill="GraphQL", confidence=MatchConfidence.matched),
        ],
        missing_required=[],
    )
    partial_match = MatchResult(
        matched_skills=[
            SkillMatch(resume_skill="React", jd_skill="React", confidence=MatchConfidence.matched),
            SkillMatch(resume_skill="TypeScript", jd_skill="TypeScript", confidence=MatchConfidence.matched),
        ],
        missing_required=[
            SkillMatch(jd_skill="GraphQL", confidence=MatchConfidence.missing),
        ],
    )
    profile = _base_profile()
    reqs = _base_requirements()

    full_score, _ = compute_scores(full_match, profile, reqs)
    partial_score, _ = compute_scores(partial_match, profile, reqs)
    assert partial_score < full_score


def test_experience_score_seniority_alignment():
    match = MatchResult(matched_skills=[])
    profile = _base_profile(seniority_level=SeniorityLevel.senior, years_experience=8.0)
    reqs = _base_requirements(seniority_level=SeniorityLevel.mid, min_years_experience=3.0)
    _, cats = compute_scores(match, profile, reqs)
    assert cats.experience >= 80.0
