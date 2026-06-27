"""오케스트레이션 — fetch → dedup → enrich → 신규필터 → 랭킹 → 요약 → Entry.

엔트리포인트(backfill/weekly/monthly)가 공통으로 호출한다.
skip_llm=True면 Claude 호출 없이 키워드 점수로 근사(비용 없는 dry-run용).
"""
from __future__ import annotations

import logging
import os

from .rank import ScoredPaper, claude_rank, prefilter
from .record import Entry
from .sources import openalex, semanticscholar
from .sources.base import dedup
from .summarize import KoreanSummary, summarize

log = logging.getLogger(__name__)


def _mailto() -> str | None:
    return os.environ.get("OPENALEX_MAILTO")


def _approx_summary(s: ScoredPaper) -> KoreanSummary:
    """skip_llm용 — abstract/tldr를 그대로 요약 자리에 사용."""
    text = s.paper.extra.get("tldr") or (s.paper.abstract or "")[:300]
    return KoreanSummary(summary=text)


def run(
    profile: dict,
    *,
    canon: list[dict] | None = None,
    year_from: int,
    year_to: int | None = None,
    seen: set[str] | None = None,
    limit: int | None = None,
    skip_llm: bool = False,
) -> tuple[list[Entry], set[str]]:
    """파이프라인 실행. (entries, 처리한 key 집합)을 반환."""
    seen = seen or set()
    keywords = profile.get("keywords", [])
    allowlist = profile.get("journal_allowlist", [])
    rcfg = profile.get("ranking", {})
    threshold = rcfg.get("relevance_threshold", 60)
    top_n = rcfg.get("keyword_top_n", 120)
    mailto = _mailto()

    # 1. fetch
    log.info("OpenAlex 검색: %d개 키워드, %s~%s", len(keywords), year_from, year_to or "현재")
    papers = openalex.search(keywords, year_from=year_from, year_to=year_to,
                             mailto=mailto, per_keyword_limit=top_n * 2)

    canon_keys: set[str] = set()
    canon_papers = []
    for c in (canon or []):
        cp = openalex.fetch_by_doi(c.get("doi", ""), mailto=mailto)
        if cp:
            canon_papers.append(cp)
            canon_keys.add(cp.key())
        else:
            log.warning("canon DOI 조회 실패: %s", c.get("doi"))
    papers += canon_papers

    # 2. dedup
    papers = dedup(papers)
    log.info("dedup 후 %d편", len(papers))

    # 3. 신규만 (이미 처리한 논문 제외)
    papers = [p for p in papers if p.key() not in seen]
    log.info("신규 %d편", len(papers))
    if not papers:
        return [], set()

    # 4. 1차 키워드 prefilter (canon은 무조건 포함)
    candidates = prefilter(papers, keywords, allowlist, top_n=top_n)
    cand_keys = {s.paper.key() for s in candidates}
    for p in papers:
        if p.key() in canon_keys and p.key() not in cand_keys:
            candidates.append(ScoredPaper(paper=p, keyword_score=99.0))
    for s in candidates:
        s.is_canon = s.paper.key() in canon_keys

    if limit:
        candidates = candidates[:limit]
    log.info("랭킹 후보 %d편", len(candidates))

    # 5. abstract 보완 (S2) — 후보로 좁힌 뒤에만 (비용/속도)
    semanticscholar.enrich([s.paper for s in candidates],
                           api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"))

    # 6. 2차 랭킹
    if skip_llm:
        for s in candidates:
            s.relevance = min(100, int(s.keyword_score * 15))
            s.reason = "(키워드 기반 근사)"
    else:
        claude_rank(candidates, profile)

    # 7. 임계값 필터 (canon은 통과)
    kept = [s for s in candidates if s.relevance >= threshold or s.is_canon]
    log.info("임계값(%d) 통과 %d편", threshold, len(kept))

    # 8. 요약
    entries: list[Entry] = []
    for s in kept:
        summ = _approx_summary(s) if skip_llm else summarize(s, profile)
        entries.append(Entry(scored=s, summary=summ))

    # 처리한 key: 랭킹 후보 전체를 seen에 기록(임계값 미달도 재평가 방지)
    processed = {s.paper.key() for s in candidates}
    entries.sort(key=lambda e: e.scored.relevance, reverse=True)
    return entries, processed
