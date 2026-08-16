from app.extraction.analyze import stub_analyze_response
from app.extraction.schemas import AnalyzeResponse


def test_stub_response_validates():
    resp = stub_analyze_response()
    assert isinstance(resp, AnalyzeResponse)
    assert 0 <= resp.overall_score <= 100
    assert resp.matching_stubbed is True
    assert resp.profile is not None
    assert "React" in resp.profile.skills
