"""오케스트레이션 (LLM 미사용) — fetch → dedup → 신규필터 → prefilter → 관련도 → 요약.

엔트리포인트(backfill/weekly/monthly)가 공통으로 호출한다.
관련도·요약 모두 키워드 휴리스틱 기반 — 외부 LLM 키 불필요.
"""
from __future__ import annotations

import logging
import os

from .rank import ScoredPaper, assign_relevance, prefilter
from .record import Entry
from .sources import openalex, semanticscholar
from .sources.base import dedup
from .summarize import summarize

log = logging.getLogger(__name__)


def _mailto() -> str | None:
    return os.environ.get("OPENALEX_MAILTO")


def weekly_selection(entries, processed, weekly_max):
    """주간 — 상위 weekly_max만 전달, 나머지는 모두 seen 처리(초과분 폐기, 이월 없음).

    (delivered, seen_add) 반환. seen_add = 평가한 전체 후보(전달분 포함).
    """
    return entries[:weekly_max], set(processed)


def run(
    profile: dict,
    *,
    canon: list[dict] | None = None,
    year_from: int,
    year_to: int | None = None,
    seen: set[str] | None = None,
    limit: int | None = None,
) -> tuple[list[Entry], set[str]]:
    """파이프라인 실행. (entries, 처리한 key 집합)을 반환."""
    seen = seen or set()
    keywords = profile.get("keywords", [])
    rcfg = profile.get("ranking", {})
    threshold = rcfg.get("relevance_threshold", 45)
    top_n = rcfg.get("keyword_top_n", 800)
    per_kw = rcfg.get("per_keyword_fetch", 400)
    mailto = _mailto()

    # 1. fetch
    log.info("OpenAlex 검색: %d개 키워드, %s~%s", len(keywords), year_from, year_to or "현재")
    papers = openalex.search(keywords, year_from=year_from, year_to=year_to,
                             mailto=mailto, per_keyword_limit=per_kw)

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
    candidates = prefilter(papers, profile, top_n=top_n)
    cand_keys = {s.paper.key() for s in candidates}
    for p in papers:
        if p.key() in canon_keys and p.key() not in cand_keys:
            candidates.append(ScoredPaper(paper=p, keyword_score=99.0))
    for s in candidates:
        s.is_canon = s.paper.key() in canon_keys

    if limit:
        candidates = candidates[:limit]
    log.info("랭킹 후보 %d편", len(candidates))

    # 5. abstract/TLDR 보완 (S2) — 후보로 좁힌 뒤에만
    semanticscholar.enrich([s.paper for s in candidates],
                           api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"))

    # 6. 관련도 (휴리스틱)
    assign_relevance(candidates, profile)

    # 7. 임계값 필터 (canon은 통과)
    kept = [s for s in candidates if s.relevance >= threshold or s.is_canon]
    log.info("임계값(%d) 통과 %d편", threshold, len(kept))

    # 8. 요약 (휴리스틱)
    entries = [Entry(scored=s, summary=summarize(s, profile)) for s in kept]

    # 처리한 key: 랭킹 후보 전체를 seen에 기록(임계값 미달도 재평가 방지)
    processed = {s.paper.key() for s in candidates}
    entries.sort(key=lambda e: e.scored.relevance, reverse=True)
    return entries, processed
