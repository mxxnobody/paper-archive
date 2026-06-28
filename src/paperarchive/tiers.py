"""티어 분류 — 관련도 순위 기반.

store(dict 리스트)에 tier 필드를 채운다:
- canon(is_canon)        → "F" (Foundational)
- 비canon 관련도 1~t1위  → 1
- t1+1 ~ t1+t2위         → 2
- 나머지                  → 3
순수 함수(외부 의존 없음).
"""
from __future__ import annotations

TIER_LABELS = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3", "F": "Foundational"}


def assign_tiers(store: list[dict], tier1_size: int = 25, tier2_size: int = 75) -> list[dict]:
    canon = [d for d in store if d.get("is_canon")]
    non_canon = [d for d in store if not d.get("is_canon")]
    non_canon.sort(key=lambda d: (d.get("relevance", 0), d.get("cited_by", 0)), reverse=True)
    for i, d in enumerate(non_canon):
        if i < tier1_size:
            d["tier"] = 1
        elif i < tier1_size + tier2_size:
            d["tier"] = 2
        else:
            d["tier"] = 3
    for d in canon:
        d["tier"] = "F"
    return store
