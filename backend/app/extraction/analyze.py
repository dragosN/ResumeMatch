"""Day-2 analyze orchestration: ingest + extract + match + score + summary."""

from __future__ import annotations

from app.config import get_settings
from app.extraction.jd_parser import parse_jd
from app.extraction.resume_parser import parse_resume
from app.extraction.schemas import (
    AnalyzeResponse,
    CategoryScores,
    ExtractedProfile,
    ExtractedRequirements,
    MatchConfidence,
    SeniorityLevel,
    SkillMatch,
)
from app.llm.provider import ChatProvider, get_chat_provider
from app.matching.scorer import compute_scores
from app.matching.skill_matcher import match_skills
from app.matching.summary import generate_summary


def stub_analyze_response() -> AnalyzeResponse:
    """Hardcoded response so frontend can render without Ollama."""
    return AnalyzeResponse(
        overall_score=72.0,
        category_scores=CategoryScores(
            technical=78.0,
            experience=70.0,
            domain=65.0,
            soft=80.0,
        ),
        matched_skills=[
            SkillMatch(
                resume_skill="React",
                jd_skill="React",
                confidence=MatchConfidence.matched,
                similarity=1.0,
            ),
            SkillMatch(
                resume_skill="TypeScript",
                jd_skill="TypeScript",
                confidence=MatchConfidence.matched,
                similarity=1.0,
            ),
        ],
        missing_required=[
            SkillMatch(
                resume_skill=None,
                jd_skill="GraphQL",
                confidence=MatchConfidence.missing,
            ),
        ],
        missing_nice_to_have=[
            SkillMatch(
                resume_skill=None,
                jd_skill="Next.js",
                confidence=MatchConfidence.missing,
            ),
        ],
        overqualified=["Kubernetes"],
        review_band=[
            SkillMatch(
                resume_skill="component-based UI",
                jd_skill="React",
                confidence=MatchConfidence.review,
                similarity=0.72,
                reason="Possible semantic match — needs review",
            ),
        ],
        summary=(
            "You are a solid technical match on React and TypeScript, but the role "
            "requires GraphQL which does not appear on your resume. Highlight any "
            "API client work and consider a tailored bullet that uses the JD's phrasing."
        ),
        profile=ExtractedProfile(
            skills=["React", "TypeScript", "Node", "Kubernetes"],
            years_experience=5.0,
            seniority_level=SeniorityLevel.mid,
            roles=["Frontend Engineer"],
            education=["B.S. Computer Science"],
            summary="Mid-level frontend engineer.",
        ),
        requirements=ExtractedRequirements(
            required_skills=["React", "TypeScript", "GraphQL"],
            nice_to_have_skills=["Next.js"],
            min_years_experience=4.0,
            seniority_level=SeniorityLevel.mid,
            responsibilities=["Build product UI"],
            ats_phrases=["React", "TypeScript", "GraphQL", "Next.js"],
        ),
        matching_stubbed=True,
    )


def analyze_texts(
    resume_text: str,
    jd_text: str,
    *,
    chat: ChatProvider | None = None,
) -> AnalyzeResponse:
    """Extract profile + requirements, run layered matching, score, and summarize."""
    settings = get_settings()
    provider = chat or get_chat_provider()
    profile = parse_resume(resume_text, provider)
    requirements = parse_jd(jd_text, provider)

    match = match_skills(
        profile,
        requirements,
        chat=provider,
        match_threshold=settings.match_threshold,
        review_threshold=settings.review_threshold,
        use_arbiter=settings.matching_use_arbiter,
    )
    overall, category_scores = compute_scores(match, profile, requirements)
    summary = generate_summary(
        match,
        overall,
        category_scores,
        profile,
        requirements,
        provider,
    )

    return AnalyzeResponse(
        overall_score=overall,
        category_scores=category_scores,
        matched_skills=match.matched_skills,
        missing_required=match.missing_required,
        missing_nice_to_have=match.missing_nice_to_have,
        overqualified=match.overqualified,
        review_band=match.review_band,
        summary=summary,
        profile=profile,
        requirements=requirements,
        ats_flags=[],
        rewrite_suggestions=[],
        matching_stubbed=False,
    )
