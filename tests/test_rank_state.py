from paperarchive.rank import prefilter, weighted_score
from paperarchive.sources.base import Paper
from paperarchive.state import filter_new

KEYWORDS = ["venture capital", "market traction", "follow-on", "machine learning",
            "south korea"]
CORE = ["market traction", "follow-on", "venture capital"]
PROFILE = {
    "keywords": KEYWORDS,
    "core_keywords": CORE,
    "journal_allowlist": ["Journal of Finance"],
    "ranking": {"core_weight": 2, "min_weight": 2},
}


def test_weighted_score_core_vs_normal():
    p = Paper(title="market traction in startups")          # 1 core
    w, hits = weighted_score(p, KEYWORDS, CORE, 2)
    assert w == 2.0 and hits == 1
    p2 = Paper(title="machine learning and south korea")    # 2 normal
    w2, hits2 = weighted_score(p2, KEYWORDS, CORE, 2)
    assert w2 == 2.0 and hits2 == 2


def test_prefilter_keeps_single_core_drops_single_normal():
    core1 = Paper(title="market traction study")            # core -> weighted 2 -> keep
    normal1 = Paper(title="machine learning only")          # normal -> weighted 1 -> drop
    out = prefilter([core1, normal1], PROFILE, top_n=10)
    assert [s.paper for s in out] == [core1]


def test_prefilter_allowlist_bonus_and_sort():
    a = Paper(title="venture capital market traction", venue="Journal of Finance")  # 2 core=4 +1 allow
    b = Paper(title="venture capital follow-on", cited_by=5)                        # 2 core=4
    out = prefilter([b, a], PROFILE, top_n=10)
    assert out[0].paper is a          # allowlist bonus floats a above b


def test_filter_new_excludes_seen():
    a = Paper(title="X", doi="10.1/a")
    b = Paper(title="Y", doi="10.1/b")
    out = filter_new([a, b], {a.key()})
    assert out == [b]
