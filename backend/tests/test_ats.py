from app.extraction.schemas import ExtractedRequirements
from app.matching.ats import check_ats_phrases


def test_ats_finds_literal_phrases():
    resume = "Built dashboards with React and TypeScript for 5 years."
    reqs = ExtractedRequirements(
        required_skills=["React"],
        ats_phrases=["React", "GraphQL", "TypeScript"],
    )
    flags = check_ats_phrases(resume, reqs)
    by_phrase = {f.phrase: f.found_in_resume for f in flags}
    assert by_phrase["React"] is True
    assert by_phrase["TypeScript"] is True
    assert by_phrase["GraphQL"] is False


def test_ats_case_insensitive():
    resume = "experience with react and node.js"
    reqs = ExtractedRequirements(ats_phrases=["React", "Node.js"])
    flags = check_ats_phrases(resume, reqs)
    assert all(f.found_in_resume for f in flags)


def test_ats_falls_back_to_required_skills():
    resume = "Python and Django developer"
    reqs = ExtractedRequirements(
        required_skills=["Python", "Rust"],
        ats_phrases=[],
    )
    flags = check_ats_phrases(resume, reqs)
    assert len(flags) == 2
    assert flags[0].found_in_resume is True
    assert flags[1].found_in_resume is False
