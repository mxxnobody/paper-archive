from paperarchive.rank import ScoredPaper, assign_relevance, prefilter
from paperarchive.sources.base import Paper
from paperarchive.summarize import summarize

PROFILE = {
    "keywords": ["venture capital", "market traction", "follow-on", "machine learning"],
    "core_keywords": ["market traction", "follow-on", "venture capital"],
    "journal_allowlist": ["Journal of Finance"],
    "ranking": {"core_weight": 2, "min_weight": 2, "saturate_weight": 5},
}


def test_assign_relevance_scores_and_reason():
    p = Paper(title="Venture capital, market traction and follow-on funding",
              abstract="We use machine learning.", venue="Journal of Finance",
              year=2024, cited_by=120)
    cands = prefilter([p], PROFILE, top_n=10)
    assign_relevance(cands, PROFILE)
    s = cands[0]
    assert s.relevance == 100          # weighted 7 / saturate 5 -> capped 100
    assert "키워드 4개" in s.reason
    assert "핵심 저널" in s.reason


def test_assign_relevance_single_core_below_max():
    p = Paper(title="market traction only", venue="Unknown J", year=2000, cited_by=0)
    cands = prefilter([p], PROFILE, top_n=10)
    assign_relevance(cands, PROFILE)
    # weighted 2 / saturate 5 = 40, no bonuses
    assert cands[0].relevance == 40


def test_summarize_detects_vars_and_method():
    p = Paper(title="Staging and follow-on rounds",
              abstract="We study follow-on investment and market traction using regression.")
    summ = summarize(ScoredPaper(paper=p), PROFILE)
    assert "후속투자" in summ.dependent_var
    assert "market traction" in summ.independent_var
    assert "회귀분석" in summ.method
    assert summ.summary


def test_summarize_prefers_tldr():
    p = Paper(title="X", abstract="long abstract", extra={"tldr": "short tldr"})
    summ = summarize(ScoredPaper(paper=p), PROFILE)
    assert summ.summary == "short tldr"
