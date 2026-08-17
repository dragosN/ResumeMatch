from app.extraction.schemas import (
    ExtractedProfile,
    ExtractedRequirements,
    MatchConfidence,
    SeniorityLevel,
)
from app.matching.skill_matcher import classify_pair, match_skills
from tests.conftest import FakeEmbeddingProvider


def test_classify_exact_match():
    conf, reason = classify_pair("React", "React.js", similarity=0.5)
    assert conf == MatchConfidence.matched
    assert "synonym" in reason.lower() or "exact" in reason.lower()


def test_classify_confusable_goes_to_review():
    conf, _ = classify_pair("Java", "JavaScript", similarity=0.95)
    assert conf == MatchConfidence.review


def test_classify_high_similarity_match():
    conf, _ = classify_pair("component-based UI", "React framework", similarity=0.90)
    assert conf == MatchConfidence.matched


def test_classify_review_band():
    conf, _ = classify_pair("Docker", "Kubernetes", similarity=0.72)
    assert conf == MatchConfidence.review


def test_classify_below_threshold_missing():
    conf, _ = classify_pair("Python", "Ruby", similarity=0.40)
    assert conf == MatchConfidence.missing


def test_match_skills_synonym_and_embedding():
    profile = ExtractedProfile(
        skills=["React.js", "TypeScript", "component-based UI development"],
        years_experience=5.0,
        seniority_level=SeniorityLevel.mid,
        roles=["Frontend Engineer"],
        education=[],
        summary="",
    )
    requirements = ExtractedRequirements(
        required_skills=["React", "GraphQL"],
        nice_to_have_skills=["JavaScript"],
        min_years_experience=3.0,
        seniority_level=SeniorityLevel.mid,
        responsibilities=[],
        ats_phrases=[],
    )
    result = match_skills(
        profile,
        requirements,
        embedder=FakeEmbeddingProvider(),
        chat=None,
        use_arbiter=False,
    )
    matched_jd = {m.jd_skill for m in result.matched_skills}
    assert "React" in matched_jd
    assert any(m.jd_skill == "GraphQL" for m in result.missing_required)


def test_java_javascript_not_auto_matched():
    profile = ExtractedProfile(
        skills=["Java"],
        years_experience=5.0,
        seniority_level=SeniorityLevel.mid,
        roles=[],
        education=[],
        summary="",
    )
    requirements = ExtractedRequirements(
        required_skills=["JavaScript"],
        nice_to_have_skills=[],
        responsibilities=[],
        ats_phrases=[],
    )
    result = match_skills(
        profile,
        requirements,
        embedder=FakeEmbeddingProvider(),
        chat=None,
        use_arbiter=False,
    )
    assert not any(m.confidence == MatchConfidence.matched for m in result.matched_skills)
    assert result.review_band or result.missing_required


def test_match_react_vs_react_js():
    profile = ExtractedProfile(
        skills=["React", "TypeScript"],
        years_experience=4.0,
        seniority_level=SeniorityLevel.mid,
        roles=[],
        education=[],
        summary="",
    )
    requirements = ExtractedRequirements(
        required_skills=["React.js", "JavaScript"],
        nice_to_have_skills=[],
        responsibilities=[],
        ats_phrases=[],
    )
    result = match_skills(
        profile,
        requirements,
        embedder=FakeEmbeddingProvider(),
        chat=None,
        use_arbiter=False,
    )
    matched = {m.jd_skill for m in result.matched_skills}
    assert "React.js" in matched
    assert "JavaScript" in matched
    assert result.missing_required == []


def test_javascript_does_not_imply_typescript():
    profile = ExtractedProfile(
        skills=["JavaScript"],
        years_experience=3.0,
        seniority_level=SeniorityLevel.mid,
        roles=[],
        education=[],
        summary="",
    )
    requirements = ExtractedRequirements(
        required_skills=["TypeScript"],
        nice_to_have_skills=[],
        responsibilities=[],
        ats_phrases=[],
    )
    result = match_skills(
        profile,
        requirements,
        embedder=FakeEmbeddingProvider(),
        chat=None,
        use_arbiter=False,
    )
    assert not any(m.jd_skill == "TypeScript" and m.confidence == MatchConfidence.matched for m in result.matched_skills)


def test_frontend_stack_covers_react_html_css_js():
    profile = ExtractedProfile(
        skills=[
            "React",
            "Next.js",
            "TypeScript",
            "TailwindCSS",
            "Three.js",
            "React Three Fiber",
            "Fabric.js",
            "React Query",
            "TanStack Router",
            "Radix UI",
            "Recharts",
            "React DnD",
            "Zod",
            "React Hook Form",
        ],
        years_experience=5.0,
        seniority_level=SeniorityLevel.mid,
        roles=[],
        education=[],
        summary="",
    )
    requirements = ExtractedRequirements(
        required_skills=["React.js", "HTML", "CSS", "JavaScript"],
        nice_to_have_skills=[],
        responsibilities=[],
        ats_phrases=[],
    )
    result = match_skills(
        profile,
        requirements,
        embedder=FakeEmbeddingProvider(),
        chat=None,
        use_arbiter=False,
    )
    missing = {m.jd_skill for m in result.missing_required}
    assert missing == set()
    matched = {m.jd_skill for m in result.matched_skills}
    assert matched == {"React.js", "HTML", "CSS", "JavaScript"}


def test_frontend_stack_covers_noisy_combined_jd_skill():
    profile = ExtractedProfile(
        skills=["React", "Next.js", "TypeScript", "TailwindCSS"],
        years_experience=5.0,
        seniority_level=SeniorityLevel.mid,
        roles=[],
        education=[],
        summary="",
    )
    requirements = ExtractedRequirements(
        required_skills=["Proficiency in React.js, HTML, CSS and JavaScript"],
        nice_to_have_skills=[],
        responsibilities=[],
        ats_phrases=[],
    )
    result = match_skills(
        profile,
        requirements,
        embedder=FakeEmbeddingProvider(),
        chat=None,
        use_arbiter=False,
    )
    assert result.missing_required == []
    assert len(result.matched_skills) == 1
