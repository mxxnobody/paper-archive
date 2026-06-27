"""공통 Paper 스키마와 dedup 유틸리티.

모든 소스(OpenAlex, Semantic Scholar)는 Paper 객체 리스트를 반환한다.
하위 파이프라인(rank/summarize/outputs)은 이 스키마에만 의존한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Paper:
    """한 편의 논문을 표현하는 소스-독립적 스키마."""

    title: str
    doi: str | None = None          # 소문자, "10..." 형식 (URL 프리픽스 제거)
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None        # 저널/학회명
    abstract: str | None = None
    url: str | None = None          # landing page (DOI 우선)
    source: str = ""                # "openalex" | "semanticscholar"
    concepts: list[str] = field(default_factory=list)  # 토픽/concept 라벨
    cited_by: int = 0
    extra: dict = field(default_factory=dict)  # tldr 등 소스별 부가정보

    def key(self) -> str:
        """dedup 키: DOI가 있으면 DOI, 없으면 정규화 제목."""
        if self.doi:
            return f"doi:{self.doi}"
        return f"title:{normalize_title(self.title)}"


def normalize_doi(raw: str | None) -> str | None:
    """DOI를 소문자 + 프리픽스 제거된 표준형으로."""
    if not raw:
        return None
    doi = raw.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:", "", doi)
    return doi or None


def normalize_title(title: str) -> str:
    """제목 기반 dedup용 정규화: 소문자, 영숫자만."""
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def dedup(papers: list[Paper]) -> list[Paper]:
    """동일 key의 논문을 병합한다. 먼저 온 항목을 유지하되 빈 필드는 뒤 항목으로 보완."""
    merged: dict[str, Paper] = {}
    for p in papers:
        k = p.key()
        if k not in merged:
            merged[k] = p
            continue
        existing = merged[k]
        # 빈 필드 보완 (예: OpenAlex에 abstract 없고 S2에 있을 때)
        if not existing.abstract and p.abstract:
            existing.abstract = p.abstract
        if not existing.doi and p.doi:
            existing.doi = p.doi
        if existing.cited_by == 0 and p.cited_by:
            existing.cited_by = p.cited_by
        if not existing.extra.get("tldr") and p.extra.get("tldr"):
            existing.extra["tldr"] = p.extra["tldr"]
    return list(merged.values())
