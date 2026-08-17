"""Layered skill matcher: normalize → synonyms → embeddings → confusables → LLM arbiter."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.extraction.schemas import (
    ExtractedProfile,
    ExtractedRequirements,
    MatchConfidence,
    SkillMatch,
)
from app.llm.provider import ChatProvider, EmbeddingProvider, get_embedding_provider
from app.matching.arbiter import arbitrate_match
from app.matching.confusables import is_confusable_pair
from app.matching.embeddings import best_similarity
from app.matching.normalize import (
    canonical_skill,
    expand_skill,
    implied_skills,
    is_weaker_than_requirement,
    skill_satisfies,
    satisfaction_reason,
)


@dataclass
class MatchResult:
    matched_skills: list[SkillMatch] = field(default_factory=list)
    missing_required: list[SkillMatch] = field(default_factory=list)
    missing_nice_to_have: list[SkillMatch] = field(default_factory=list)
    review_band: list[SkillMatch] = field(default_factory=list)
    overqualified: list[str] = field(default_factory=list)


@dataclass
class _PairDecision:
    jd_skill: str
    confidence: MatchConfidence
    resume_skill: str | None = None
    similarity: float | None = None
    reason: str | None = None


def match_skills(
    profile: ExtractedProfile,
    requirements: ExtractedRequirements,
    *,
    embedder: EmbeddingProvider | None = None,
    chat: ChatProvider | None = None,
    match_threshold: float = 0.85,
    review_threshold: float = 0.65,
    use_arbiter: bool = True,
) -> MatchResult:
    """Match resume skills against JD requirements using the layered pipeline."""
    resume_skills = profile.skills
    if not resume_skills:
        return _all_missing(requirements)

    embedding_provider = embedder or get_embedding_provider()
    all_skills = list(dict.fromkeys(resume_skills + requirements.required_skills + requirements.nice_to_have_skills))
    vectors = embedding_provider.embed(all_skills)
    skill_to_vector = dict(zip(all_skills, vectors))
    resume_vectors = [skill_to_vector[s] for s in resume_skills]

    matched_resume_indices: set[int] = set()
    required_decisions: list[_PairDecision] = []
    nice_decisions: list[_PairDecision] = []

    for jd_skill in requirements.required_skills:
        decision = _match_one_jd_skill(
            jd_skill,
            resume_skills,
            resume_vectors,
            skill_to_vector,
            match_threshold=match_threshold,
            review_threshold=review_threshold,
            chat=chat if use_arbiter else None,
        )
        required_decisions.append(decision)
        if decision.resume_skill is not None:
            for idx, rs in enumerate(resume_skills):
                if rs == decision.resume_skill:
                    matched_resume_indices.add(idx)
                    break

    for jd_skill in requirements.nice_to_have_skills:
        if _already_covered(jd_skill, required_decisions):
            continue
        decision = _match_one_jd_skill(
            jd_skill,
            resume_skills,
            resume_vectors,
            skill_to_vector,
            match_threshold=match_threshold,
            review_threshold=review_threshold,
            chat=chat if use_arbiter else None,
        )
        nice_decisions.append(decision)
        if decision.resume_skill is not None and decision.confidence == MatchConfidence.matched:
            for idx, rs in enumerate(resume_skills):
                if rs == decision.resume_skill:
                    matched_resume_indices.add(idx)
                    break

    overqualified = [
        resume_skills[i]
        for i in range(len(resume_skills))
        if i not in matched_resume_indices
        and not _skill_mentioned_in_requirements(resume_skills[i], requirements)
    ]

    return MatchResult(
        matched_skills=_collect(required_decisions + nice_decisions, MatchConfidence.matched),
        missing_required=_collect(required_decisions, MatchConfidence.missing),
        missing_nice_to_have=_collect(nice_decisions, MatchConfidence.missing),
        review_band=_collect(required_decisions + nice_decisions, MatchConfidence.review),
        overqualified=overqualified,
    )


def classify_pair(
    resume_skill: str,
    jd_skill: str,
    similarity: float,
    *,
    match_threshold: float = 0.85,
    review_threshold: float = 0.65,
) -> tuple[MatchConfidence, str | None]:
    """Classify a single resume/JD pair (used by eval set — no embeddings call)."""
    if skill_satisfies(resume_skill, jd_skill):
        return MatchConfidence.matched, satisfaction_reason(resume_skill, jd_skill)

    if is_weaker_than_requirement(resume_skill, jd_skill):
        return MatchConfidence.missing, f"{resume_skill} does not cover {jd_skill}"

    if is_confusable_pair(resume_skill, jd_skill):
        return MatchConfidence.review, "Known confusable pair — needs review"

    if similarity >= match_threshold:
        return MatchConfidence.matched, f"Embedding similarity {similarity:.2f}"
    if similarity >= review_threshold:
        return MatchConfidence.review, f"Embedding similarity {similarity:.2f} — review band"
    return MatchConfidence.missing, f"Below review threshold ({similarity:.2f})"


def _match_one_jd_skill(
    jd_skill: str,
    resume_skills: list[str],
    resume_vectors: list[list[float]],
    skill_to_vector: dict[str, list[float]],
    *,
    match_threshold: float,
    review_threshold: float,
    chat: ChatProvider | None,
) -> _PairDecision:
    # Layer 1: exact / synonym / implication (TypeScript → JavaScript, React ↔ React.js)
    covering = _covering_resume_skill(jd_skill, resume_skills)
    if covering is not None:
        return _PairDecision(
            resume_skill=covering,
            jd_skill=jd_skill,
            confidence=MatchConfidence.matched,
            similarity=1.0,
            reason=satisfaction_reason(covering, jd_skill),
        )

    jd_vector = skill_to_vector.get(jd_skill)
    if jd_vector is None:
        return _PairDecision(jd_skill=jd_skill, confidence=MatchConfidence.missing, reason="No embedding")

    best_idx, best_sim = best_similarity(jd_vector, resume_vectors)
    if best_idx < 0:
        return _PairDecision(jd_skill=jd_skill, confidence=MatchConfidence.missing)

    best_resume = resume_skills[best_idx]

    if is_weaker_than_requirement(best_resume, jd_skill):
        return _PairDecision(
            jd_skill=jd_skill,
            confidence=MatchConfidence.missing,
            resume_skill=best_resume,
            similarity=best_sim,
            reason=f"{best_resume} does not cover {jd_skill}",
        )

    if is_confusable_pair(best_resume, jd_skill):
        if chat is not None:
            is_match, reason = arbitrate_match(best_resume, jd_skill, similarity=best_sim, chat=chat)
            if is_match:
                return _PairDecision(
                    resume_skill=best_resume,
                    jd_skill=jd_skill,
                    confidence=MatchConfidence.matched,
                    similarity=best_sim,
                    reason=f"LLM arbiter: {reason}",
                )
        return _PairDecision(
            resume_skill=best_resume,
            jd_skill=jd_skill,
            confidence=MatchConfidence.review,
            similarity=best_sim,
            reason="Known confusable pair — embedding alone insufficient",
        )

    confidence, reason = classify_pair(
        best_resume,
        jd_skill,
        best_sim,
        match_threshold=match_threshold,
        review_threshold=review_threshold,
    )

    if confidence == MatchConfidence.review and chat is not None:
        is_match, arb_reason = arbitrate_match(best_resume, jd_skill, similarity=best_sim, chat=chat)
        if is_match:
            return _PairDecision(
                resume_skill=best_resume,
                jd_skill=jd_skill,
                confidence=MatchConfidence.matched,
                similarity=best_sim,
                reason=f"LLM arbiter: {arb_reason}",
            )
        return _PairDecision(
            resume_skill=best_resume,
            jd_skill=jd_skill,
            confidence=MatchConfidence.review,
            similarity=best_sim,
            reason=f"Review band — arbiter declined: {arb_reason}",
        )

    if confidence == MatchConfidence.matched:
        return _PairDecision(
            resume_skill=best_resume,
            jd_skill=jd_skill,
            confidence=MatchConfidence.matched,
            similarity=best_sim,
            reason=reason,
        )
    if confidence == MatchConfidence.review:
        return _PairDecision(
            resume_skill=best_resume,
            jd_skill=jd_skill,
            confidence=MatchConfidence.review,
            similarity=best_sim,
            reason=reason,
        )
    return _PairDecision(jd_skill=jd_skill, confidence=MatchConfidence.missing, reason=reason)


def _all_missing(requirements: ExtractedRequirements) -> MatchResult:
    return MatchResult(
        missing_required=[
            SkillMatch(jd_skill=s, confidence=MatchConfidence.missing) for s in requirements.required_skills
        ],
        missing_nice_to_have=[
            SkillMatch(jd_skill=s, confidence=MatchConfidence.missing)
            for s in requirements.nice_to_have_skills
        ],
    )


def _collect(decisions: list[_PairDecision], confidence: MatchConfidence) -> list[SkillMatch]:
    return [
        SkillMatch(
            resume_skill=d.resume_skill,
            jd_skill=d.jd_skill,
            confidence=d.confidence,
            similarity=d.similarity,
            reason=d.reason,
        )
        for d in decisions
        if d.confidence == confidence
    ]


def _covering_resume_skill(jd_skill: str, resume_skills: list[str]) -> str | None:
    """First resume skill that covers the JD skill, or a contributor if coverage is combined."""
    for rs in resume_skills:
        if skill_satisfies(rs, jd_skill):
            return rs
    jd_tokens = set(expand_skill(jd_skill))
    if not jd_tokens:
        return None
    covered: set[str] = set()
    contributor: str | None = None
    for rs in resume_skills:
        implied = implied_skills(rs)
        if implied & jd_tokens:
            covered |= implied
            contributor = contributor or rs
        if jd_tokens <= covered:
            return contributor
    return None


def _already_covered(jd_skill: str, required_decisions: list[_PairDecision]) -> bool:
    jd_canon = canonical_skill(jd_skill)
    for d in required_decisions:
        if d.confidence in {MatchConfidence.matched, MatchConfidence.review}:
            if skill_satisfies(d.jd_skill, jd_skill) or canonical_skill(d.jd_skill) == jd_canon:
                return True
    return False


def _skill_mentioned_in_requirements(skill: str, requirements: ExtractedRequirements) -> bool:
    all_jd = requirements.required_skills + requirements.nice_to_have_skills
    return any(skill_satisfies(skill, jd) or skill_satisfies(jd, skill) for jd in all_jd)
