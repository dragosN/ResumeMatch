from app.extraction.analyze import stub_compare_response
from app.extraction.schemas import CompareResponse


def test_stub_compare_validates():
    resp = stub_compare_response()
    assert isinstance(resp, CompareResponse)
    assert len(resp.ranked) == 3
    scores = [item.overall_score for item in resp.ranked]
    assert scores == sorted(scores, reverse=True)
    assert resp.profile is not None
    assert resp.ranked[0].result.ats_flags
    assert resp.ranked[0].result.rewrite_suggestions
