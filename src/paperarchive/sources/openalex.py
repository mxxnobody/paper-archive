"""OpenAlex Works API 소스 (주 소스, 무료·키 불필요).

키워드별로 relevance 정렬 검색 → Paper로 정규화. abstract는 inverted index에서 복원.
polite pool 사용을 위해 mailto 파라미터를 붙인다.
"""
from __future__ import annotations

import logging

import httpx

from .base import Paper, normalize_doi

log = logging.getLogger(__name__)

API = "https://api.openalex.org/works"

# 정규화에 필요한 최소 필드만 요청 → 응답 크기·속도 최적화
_SELECT = ",".join([
    "id", "doi", "title", "display_name", "publication_year",
    "authorships", "primary_location", "cited_by_count",
    "concepts", "abstract_inverted_index",
])


def _reconstruct_abstract(inverted: dict | None) -> str | None:
    """OpenAlex abstract_inverted_index({단어: [위치,...]})를 원문 순서로 복원."""
    if not inverted:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    text = " ".join(word for _, word in positions)
    return text or None


def _to_paper(w: dict) -> Paper:
    authors = [
        a.get("author", {}).get("display_name")
        for a in w.get("authorships", [])
        if a.get("author", {}).get("display_name")
    ]
    venue = None
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    venue = src.get("display_name")
    doi = normalize_doi(w.get("doi"))
    return Paper(
        title=w.get("title") or w.get("display_name") or "(제목 없음)",
        doi=doi,
        authors=authors,
        year=w.get("publication_year"),
        venue=venue,
        abstract=_reconstruct_abstract(w.get("abstract_inverted_index")),
        url=f"https://doi.org/{doi}" if doi else w.get("id"),
        source="openalex",
        concepts=[c.get("display_name") for c in w.get("concepts", []) if c.get("display_name")],
        cited_by=w.get("cited_by_count", 0) or 0,
    )


def _client(mailto: str | None) -> httpx.Client:
    headers = {"User-Agent": f"paper-archive (mailto:{mailto})"} if mailto else {}
    return httpx.Client(timeout=30.0, headers=headers)


def search(
    keywords: list[str],
    year_from: int,
    year_to: int | None = None,
    mailto: str | None = None,
    per_keyword_limit: int = 200,
) -> list[Paper]:
    """키워드별 relevance 정렬 검색 결과를 합쳐 반환(dedup은 호출측 책임)."""
    papers: list[Paper] = []
    date_filter = f"from_publication_date:{year_from}-01-01"
    if year_to:
        date_filter += f",to_publication_date:{year_to}-12-31"

    with _client(mailto) as client:
        for kw in keywords:
            fetched = 0
            cursor = "*"
            while fetched < per_keyword_limit and cursor:
                params = {
                    "search": kw,
                    "filter": date_filter,
                    "per-page": min(200, per_keyword_limit - fetched),
                    "cursor": cursor,
                    "select": _SELECT,
                    "sort": "relevance_score:desc",
                }
                if mailto:
                    params["mailto"] = mailto
                try:
                    r = client.get(API, params=params)
                    r.raise_for_status()
                except httpx.HTTPError as e:
                    log.warning("OpenAlex 검색 실패 (kw=%s): %s", kw, e)
                    break
                data = r.json()
                results = data.get("results", [])
                for w in results:
                    papers.append(_to_paper(w))
                fetched += len(results)
                cursor = data.get("meta", {}).get("next_cursor")
                if not results:
                    break
            log.info("OpenAlex '%s': %d편", kw, fetched)
    return papers


def fetch_by_doi(doi: str, mailto: str | None = None) -> Paper | None:
    """canon 적재용 — DOI 단건 조회."""
    doi = normalize_doi(doi)
    if not doi:
        return None
    with _client(mailto) as client:
        params = {"select": _SELECT}
        if mailto:
            params["mailto"] = mailto
        try:
            r = client.get(f"{API}/doi:{doi}", params=params)
            r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("OpenAlex DOI 조회 실패 (%s): %s", doi, e)
            return None
        return _to_paper(r.json())
