"""관련도 랭킹 (LLM 미사용) — 가중 키워드·저널·인용·최신성 휴리스틱.

핵심 키워드(core)는 가중치를 높여 연구 정체성에 직결된 논문을 끌어올린다.
모든 함수가 외부 의존 없는 순수 함수라 테스트 가능하다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .sources.base import Paper


@dataclass
class ScoredPaper:
    paper: Paper
    weighted: float = 0.0       # 가중 키워드 점수 (prefilter 정렬용)
    keyword_hits: int = 0
    relevance: int = 0          # 0~100 휴리스틱
    reason: str = ""            # 한국어 관련도 근거
    is_canon: bool = False


def _haystack(paper: Paper) -> str:
    return " ".join([
        paper.title or "",
        paper.abstract or "",
        paper.extra.get("tldr", ""),
        " ".join(paper.concepts),
    ]).lower()


def matched_keywords(paper: Paper, keywords: list[str]) -> list[str]:
    h = _haystack(paper)
    return [kw for kw in keywords if kw.lower() in h]


def in_allowlist(paper: Paper, allowlist: list[str]) -> bool:
    venue = (paper.venue or "").lower()
    return bool(allowlist) and any(j.lower() in venue for j in allowlist)


def weighted_score(
    paper: Paper, keywords: list[str], core: list[str], core_weight: float
) -> tuple[float, int]:
    """(가중합, 일치 키워드 수). 핵심 키워드는 core_weight, 일반은 1."""
    hits = matched_keywords(paper, keywords)
    core_lower = {c.lower() for c in core}
    total = sum(core_weight if kw.lower() in core_lower else 1.0 for kw in hits)
    return total, len(hits)


def prefilter(
    papers: list[Paper], profile: dict, top_n: int
) -> list[ScoredPaper]:
    """가중합 >= min_weight 논문을 점수순 정렬해 상위 top_n 반환."""
    keywords = profile.get("keywords", [])
    core = profile.get("core_keywords", [])
    cfg = profile.get("ranking", {})
    core_weight = cfg.get("core_weight", 2)
    min_weight = cfg.get("min_weight", 2)
    allowlist = profile.get("journal_allowlist", [])

    scored = []
    for p in papers:
        w, hits = weighted_score(p, keywords, core, core_weight)
        if w < min_weight:
            continue
        s = ScoredPaper(paper=p, weighted=w + (1.0 if in_allowlist(p, allowlist) else 0.0),
                        keyword_hits=hits)
        scored.append(s)
    scored.sort(key=lambda s: (s.weighted, s.paper.cited_by), reverse=True)
    return scored[:top_n]


def assign_relevance(candidates: list[ScoredPaper], profile: dict) -> list[ScoredPaper]:
    """휴리스틱 관련도(0~100)와 한국어 근거를 채운다."""
    keywords = profile.get("keywords", [])
    core = profile.get("core_keywords", [])
    allowlist = profile.get("journal_allowlist", [])
    cfg = profile.get("ranking", {})
    core_weight = cfg.get("core_weight", 2)
    saturate = max(1.0, cfg.get("saturate_weight", 5))
    cur_year = datetime.now(timezone.utc).year

    for s in candidates:
        p = s.paper
        hits = matched_keywords(p, keywords)
        w, _ = weighted_score(p, keywords, core, core_weight)
        s.keyword_hits = len(hits)
        base = min(100.0, 100.0 * w / saturate)
        allow = in_allowlist(p, allowlist)
        bonus_allow = 15.0 if allow else 0.0
        bonus_cite = min(10.0, math.log10(p.cited_by + 1) * 4.0)
        recency = 0.0
        if p.year and p.year >= cur_year - 3:
            recency = 8.0
        elif p.year and p.year >= cur_year - 6:
            recency = 4.0
        s.relevance = int(min(100.0, base + bonus_allow + bonus_cite + recency))

        bits = [f"키워드 {len(hits)}개 일치"]
        if hits:
            bits[0] += f" ({', '.join(hits[:4])})"
        if allow:
            bits.append("핵심 저널")
        if p.cited_by:
            bits.append(f"인용 {p.cited_by}")
        s.reason = " · ".join(bits)

    candidates.sort(key=lambda s: s.relevance, reverse=True)
    return candidates
