from paperarchive.tiers import assign_tiers


def _store(n, canon=0):
    s = [{"doi": f"10.1/{i}", "relevance": 100 - i, "is_canon": False} for i in range(n)]
    for j in range(canon):
        s.append({"doi": f"10.9/{j}", "relevance": 50, "is_canon": True})
    return s


def test_tier_boundaries():
    s = assign_tiers(_store(120), tier1_size=25, tier2_size=75)
    by_doi = {d["doi"]: d["tier"] for d in s}
    assert by_doi["10.1/0"] == 1        # rank 1
    assert by_doi["10.1/24"] == 1       # rank 25
    assert by_doi["10.1/25"] == 2       # rank 26
    assert by_doi["10.1/99"] == 2       # rank 100
    assert by_doi["10.1/100"] == 3      # rank 101


def test_canon_is_foundational_regardless_of_score():
    s = assign_tiers(_store(10, canon=3), tier1_size=25, tier2_size=75)
    canon = [d for d in s if d["is_canon"]]
    assert all(d["tier"] == "F" for d in canon)
    # 비canon은 점수가 낮아도 canon에 밀리지 않고 1로 시작
    assert any(d["tier"] == 1 for d in s if not d["is_canon"])


def test_small_archive_all_tier1():
    s = assign_tiers(_store(5), tier1_size=25, tier2_size=75)
    assert all(d["tier"] == 1 for d in s)
