from paperarchive.outputs.zotero import tier_callnumbers


def test_callnumbers_order_within_and_across_tiers():
    store = [
        {"doi": "10.1/a", "relevance": 95, "tier": 1, "cited_by": 0},
        {"doi": "10.1/b", "relevance": 99, "tier": 1, "cited_by": 0},
        {"doi": "10.1/c", "relevance": 80, "tier": 2, "cited_by": 0},
        {"doi": "10.9/x", "relevance": 50, "tier": "F", "cited_by": 0},
    ]
    cn = tier_callnumbers(store)
    # tier 1 내림차순: b(99)=001, a(95)=002
    assert cn["10.1/b"] == "T1-001"
    assert cn["10.1/a"] == "T1-002"
    assert cn["10.1/c"] == "T2-001"
    assert cn["10.9/x"] == "TF-001"
    # 정렬 시 T1 < T2 < T3 < TF
    assert sorted(cn.values()) == ["T1-001", "T1-002", "T2-001", "TF-001"]


def test_callnumbers_skips_items_without_doi():
    store = [{"doi": None, "relevance": 90, "tier": 1}, {"doi": "10.1/z", "relevance": 88, "tier": 1}]
    cn = tier_callnumbers(store)
    assert cn == {"10.1/z": "T1-001"}
