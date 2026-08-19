from app.extraction.schemas import (
    ExtractedProfile,
    ExtractedRequirements,
    MatchConfidence,
    SeniorityLevel,
    SkillMatch,
)
from app.matching.rewrite import _rewrite_targets
from app.matching.skill_matcher import MatchResult


def test_rewrite_targets_review_before_missing():
    match = MatchResult(
        review_band=[
            SkillMatch(
                resume_skill="REST",
                jd_skill="GraphQL",
                confidence=MatchConfidence.review,
            )
        ],
        missing_required=[
            SkillMatch(jd_skill="Kubernetes", confidence=MatchConfidence.missing),
        ],
    )
    targets = _rewrite_targets(match)
    assert targets[0] == "GraphQL"
    assert "Kubernetes" in targets


def test_rewrite_targets_dedupes():
    match = MatchResult(
        missing_required=[
            SkillMatch(jd_skill="GraphQL", confidence=MatchConfidence.missing),
            SkillMatch(jd_skill="graphql", confidence=MatchConfidence.missing),
        ],
    )
    targets = _rewrite_targets(match)
    assert len(targets) == 1
