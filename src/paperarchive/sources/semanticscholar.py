"""Semantic Scholar 보조 소스 — TLDR/누락 abstract 보완.

OpenAlex 결과 중 abstract가 비어 있는 논문을 DOI로 조회해 abstract와 TLDR을 채운다.
API 키는 선택(없으면 공용 rate limit). 실패는 조용히 건너뛴다(파이프라인 비차단).
"""
from __future__ import annotations

import logging

import httpx

from .base import Paper

log = logging.getLogger(__name__)

API = "https://api.semanticscholar.org/graph/v1/paper"
_FIELDS = "title,abstract,tldr,year,venue,externalIds"


def enrich(papers: list[Paper], api_key: str | None = None) -> None:
    """abstract가 없는 Paper들을 in-place로 보완. DOI 있는 항목만 대상."""
    headers = {"x-api-key": api_key} if api_key else {}
    targets = [p for p in papers if p.doi and not p.abstract]
    if not targets:
        return
    with httpx.Client(timeout=30.0, headers=headers) as client:
        for p in targets:
            try:
                r = client.get(f"{API}/DOI:{p.doi}", params={"fields": _FIELDS})
                if r.status_code == 404:
                    continue
                r.raise_for_status()
            except httpx.HTTPError as e:
                log.debug("S2 조회 실패 (%s): %s", p.doi, e)
                continue
            data = r.json()
            if data.get("abstract"):
                p.abstract = data["abstract"]
            tldr = (data.get("tldr") or {}).get("text")
            if tldr:
                p.extra["tldr"] = tldr
