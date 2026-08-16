"""Day-1 analyze orchestration: ingest + extract; match/score stubbed."""

from __future__ import annotations

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
    """Extract profile + requirements; return response with matching stubbed for Day 1."""
    provider = chat or get_chat_provider()
    profile = parse_resume(resume_text, provider)
    requirements = parse_jd(jd_text, provider)

    # Placeholder scoring until Day 2 matching lands
    matched = [
        SkillMatch(
            resume_skill=s,
            jd_skill=s,
            confidence=MatchConfidence.matched,
            similarity=1.0,
            reason="Exact string overlap (Day 1 stub matcher)",
        )
        for s in profile.skills
        if s.lower() in {r.lower() for r in requirements.required_skills}
    ]
    matched_names = {m.jd_skill.lower() for m in matched}
    missing_required = [
        SkillMatch(jd_skill=s, confidence=MatchConfidence.missing)
        for s in requirements.required_skills
        if s.lower() not in matched_names
        and s.lower() not in {p.lower() for p in profile.skills}
    ]
    missing_nth = [
        SkillMatch(jd_skill=s, confidence=MatchConfidence.missing)
        for s in requirements.nice_to_have_skills
        if s.lower() not in {p.lower() for p in profile.skills}
    ]

    req_total = max(len(requirements.required_skills), 1)
    overall = round(100.0 * (len(matched) / req_total), 1)

    summary_bits = [
        f"Extracted {len(profile.skills)} resume skills and "
        f"{len(requirements.required_skills)} required JD skills.",
        f"Exact-name overlap match score (stub): {overall}/100.",
    ]
    if profile.extraction_warnings:
        summary_bits.append("Resume extraction warnings: " + "; ".join(profile.extraction_warnings))
    if requirements.extraction_warnings:
        summary_bits.append("JD extraction warnings: " + "; ".join(requirements.extraction_warnings))
    if missing_required:
        summary_bits.append(
            "Missing required (exact-name stub): "
            + ", ".join(m.jd_skill for m in missing_required)
        )
    summary_bits.append(
        "Full semantic matching, weighted scoring, and LLM summary land on Day 2."
    )

    return AnalyzeResponse(
        overall_score=min(overall, 100.0),
        category_scores=CategoryScores(
            technical=min(overall, 100.0),
            experience=50.0,
            domain=50.0,
            soft=50.0,
        ),
        matched_skills=matched,
        missing_required=missing_required,
        missing_nice_to_have=missing_nth,
        overqualified=[],
        review_band=[],
        summary=" ".join(summary_bits),
        profile=profile,
        requirements=requirements,
        ats_flags=[],
        rewrite_suggestions=[],
        matching_stubbed=True,
    )
