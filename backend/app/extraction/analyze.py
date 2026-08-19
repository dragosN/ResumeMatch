"""Analyze orchestration: ingest + extract + match + score + summary + ATS + rewrites."""

from __future__ import annotations

from app.config import get_settings
from app.extraction.jd_parser import parse_jd
from app.extraction.resume_parser import parse_resume
from app.extraction.schemas import (
    AnalyzeResponse,
    AtsFlag,
    CategoryScores,
    CompareResponse,
    ExtractedProfile,
    ExtractedRequirements,
    JdComparisonItem,
    MatchConfidence,
    RewriteSuggestion,
    SeniorityLevel,
    SkillMatch,
)
from app.llm.provider import ChatProvider, get_chat_provider
from app.matching.ats import check_ats_phrases
from app.matching.rewrite import generate_rewrites
from app.matching.scorer import compute_scores
from app.matching.skill_matcher import MatchResult, match_skills
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
        ats_flags=[
            AtsFlag(phrase="React", found_in_resume=True),
            AtsFlag(phrase="TypeScript", found_in_resume=True),
            AtsFlag(phrase="GraphQL", found_in_resume=False),
            AtsFlag(phrase="Next.js", found_in_resume=False),
        ],
        rewrite_suggestions=[
            RewriteSuggestion(
                original="Built customer dashboards with React and REST APIs.",
                suggested=(
                    "Built customer dashboards with React and REST APIs, "
                    "including GraphQL query integration for data fetching."
                ),
                targets_skill="GraphQL",
                rationale=(
                    "Reframe existing API work with GraphQL phrasing if you have "
                    "any client-side query experience — do not claim without it."
                ),
            ),
        ],
        matching_stubbed=True,
    )


def stub_compare_response() -> CompareResponse:
    """Three ranked stub JDs for compare UI development."""
    base = stub_analyze_response()
    items = [
        JdComparisonItem(
            label="Senior React Engineer",
            overall_score=72.0,
            summary=base.summary,
            top_gaps=["GraphQL"],
            result=base,
        ),
        JdComparisonItem(
            label="Full-stack Node role",
            overall_score=58.0,
            summary="Moderate match — strong on React/TS but light on backend depth.",
            top_gaps=["PostgreSQL", "GraphQL"],
            result=_variant_stub(base, score=58.0, missing=["PostgreSQL", "GraphQL"]),
        ),
        JdComparisonItem(
            label="Frontend lead",
            overall_score=81.0,
            summary="Strong frontend overlap; leadership keywords could be stronger.",
            top_gaps=["Next.js"],
            result=_variant_stub(base, score=81.0, missing=["Next.js"]),
        ),
    ]
    items.sort(key=lambda x: x.overall_score, reverse=True)
    return CompareResponse(ranked=items, profile=base.profile)


def _variant_stub(base: AnalyzeResponse, *, score: float, missing: list[str]) -> AnalyzeResponse:
    return base.model_copy(
        update={
            "overall_score": score,
            "missing_required": [
                SkillMatch(jd_skill=s, confidence=MatchConfidence.missing) for s in missing
            ],
        }
    )


def analyze_texts(
    resume_text: str,
    jd_text: str,
    *,
    chat: ChatProvider | None = None,
    profile: ExtractedProfile | None = None,
    include_rewrites: bool = True,
) -> AnalyzeResponse:
    """Extract profile + requirements, run full pipeline including ATS and rewrites."""
    settings = get_settings()
    provider = chat or get_chat_provider()
    prof = profile or parse_resume(resume_text, provider)
    requirements = parse_jd(jd_text, provider)

    match = match_skills(
        prof,
        requirements,
        chat=provider,
        match_threshold=settings.match_threshold,
        review_threshold=settings.review_threshold,
        use_arbiter=settings.matching_use_arbiter,
    )
    overall, category_scores = compute_scores(match, prof, requirements)
    summary = generate_summary(
        match,
        overall,
        category_scores,
        prof,
        requirements,
        provider,
    )
    ats_flags = check_ats_phrases(resume_text, requirements)
    rewrites: list[RewriteSuggestion] = []
    if include_rewrites and settings.generate_rewrites:
        rewrites = generate_rewrites(match, prof, requirements, resume_text, provider)

    return AnalyzeResponse(
        overall_score=overall,
        category_scores=category_scores,
        matched_skills=match.matched_skills,
        missing_required=match.missing_required,
        missing_nice_to_have=match.missing_nice_to_have,
        overqualified=match.overqualified,
        review_band=match.review_band,
        summary=summary,
        profile=prof,
        requirements=requirements,
        ats_flags=ats_flags,
        rewrite_suggestions=rewrites,
        matching_stubbed=False,
    )


def compare_texts(
    resume_text: str,
    jd_texts: list[str],
    *,
    labels: list[str] | None = None,
    chat: ChatProvider | None = None,
) -> CompareResponse:
    """Analyze one resume against up to 3 JDs; return ranked comparison."""
    if not jd_texts:
        raise ValueError("At least one job description is required.")
    if len(jd_texts) > 3:
        raise ValueError("At most 3 job descriptions supported.")

    provider = chat or get_chat_provider()
    profile = parse_resume(resume_text, provider)
    lbls = labels or [_jd_label(t, i) for i, t in enumerate(jd_texts)]

    items: list[JdComparisonItem] = []
    for idx, jd_text in enumerate(jd_texts):
        result = analyze_texts(
            resume_text,
            jd_text,
            chat=provider,
            profile=profile,
            include_rewrites=idx == 0,
        )
        top_gaps = [m.jd_skill for m in result.missing_required[:5]]
        items.append(
            JdComparisonItem(
                label=lbls[idx] if idx < len(lbls) else _jd_label(jd_text, idx),
                overall_score=result.overall_score,
                summary=result.summary,
                top_gaps=top_gaps,
                result=result,
            )
        )

    items.sort(key=lambda x: x.overall_score, reverse=True)
    return CompareResponse(ranked=items, profile=profile)


def _jd_label(jd_text: str, index: int) -> str:
    first_line = jd_text.strip().splitlines()[0][:60] if jd_text.strip() else ""
    if first_line:
        return first_line
    return f"JD {index + 1}"
