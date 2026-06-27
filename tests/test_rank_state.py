from paperarchive.rank import keyword_score, prefilter
from paperarchive.sources.base import Paper
from paperarchive.state import filter_new


KW = ["venture capital", "market traction", "follow-on"]
ALLOW = ["Journal of Finance"]


def test_keyword_score_counts_and_allowlist_bonus():
    p = Paper(title="Venture Capital and market traction", abstract="follow-on funding",
              venue="Journal of Finance")
    # 3 keyword hits + 2 allowlist bonus
    assert keyword_score(p, KW, ALLOW) == 5.0


def test_keyword_score_zero_when_no_match():
    p = Paper(title="Unrelated biology paper", venue="Cell")
    assert keyword_score(p, KW, ALLOW) == 0.0


def test_prefilter_drops_zero_and_sorts_and_caps():
    a = Paper(title="venture capital market traction follow-on", venue="Journal of Finance")  # 5
    b = Paper(title="venture capital", cited_by=10)   # 1
    c = Paper(title="venture capital", cited_by=99)   # 1, higher cites
    d = Paper(title="nothing relevant")              # 0 -> dropped
    out = prefilter([b, a, c, d], KW, ALLOW, top_n=2)
    assert len(out) == 2
    assert out[0].paper is a               # highest keyword score first
    assert out[1].paper is c               # tie broken by cited_by


def test_filter_new_excludes_seen():
    a = Paper(title="X", doi="10.1/a")
    b = Paper(title="Y", doi="10.1/b")
    seen = {a.key()}
    out = filter_new([a, b], seen)
    assert out == [b]
