"""Zotero Web API 푸시 — read/write API 키로 지정 컬렉션에 항목 추가.

환경변수: ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_COLLECTION_KEY
이미 있는 DOI는 건너뛴다(중복 방지). 미설정 시 조용히 건너뜀(로컬 실행 편의).
"""
from __future__ import annotations

import logging
import os

from ..record import Entry

log = logging.getLogger(__name__)


def _existing_dois(zot, collection_key: str | None) -> set[str]:
    """라이브러리(또는 컬렉션)의 기존 DOI 집합 — 중복 푸시 방지."""
    dois: set[str] = set()
    try:
        items = (
            zot.collection_items_top(collection_key) if collection_key else zot.top()
        )
        for it in items:
            doi = (it.get("data", {}).get("DOI") or "").lower()
            if doi:
                dois.add(doi)
    except Exception as e:  # noqa: BLE001
        log.debug("Zotero 기존 DOI 조회 실패: %s", e)
    return dois


def _to_zotero_item(zot, e: Entry, collection_key: str | None) -> dict:
    p = e.paper
    template = zot.item_template("journalArticle")
    template["title"] = p.title
    template["creators"] = [
        {"creatorType": "author", "name": a} for a in p.authors
    ] or [{"creatorType": "author", "name": ""}]
    template["publicationTitle"] = p.venue or ""
    template["date"] = str(p.year or "")
    template["DOI"] = p.doi or ""
    template["url"] = p.url or ""
    template["abstractNote"] = p.abstract or ""
    # 태그: 관련 concept + canon 표시
    tags = [{"tag": c} for c in p.concepts[:6]]
    if e.scored.is_canon:
        tags.append({"tag": "canon"})
    tags.append({"tag": f"relevance:{e.scored.relevance}"})
    template["tags"] = tags
    template["extra"] = f"한국어요약: {e.summary.summary}\n관련도근거: {e.scored.reason}"
    if collection_key:
        template["collections"] = [collection_key]
    return template


def push(entries: list[Entry]) -> int:
    """엔트리를 Zotero에 추가. 추가된 항목 수 반환. 미설정/오류 시 0."""
    api_key = os.environ.get("ZOTERO_API_KEY")
    user_id = os.environ.get("ZOTERO_USER_ID")
    collection_key = os.environ.get("ZOTERO_COLLECTION_KEY") or None
    if not (api_key and user_id):
        log.info("Zotero 미설정 — 푸시 건너뜀.")
        return 0

    try:
        from pyzotero import zotero
    except ImportError:
        log.warning("pyzotero 미설치 — Zotero 푸시 건너뜀.")
        return 0

    zot = zotero.Zotero(user_id, "user", api_key)
    existing = _existing_dois(zot, collection_key)

    items = []
    for e in entries:
        if e.paper.doi and e.paper.doi.lower() in existing:
            continue
        items.append(_to_zotero_item(zot, e, collection_key))

    if not items:
        log.info("Zotero: 추가할 신규 항목 없음.")
        return 0

    created = 0
    # Zotero create_items는 한 번에 최대 50개
    for i in range(0, len(items), 50):
        resp = zot.create_items(items[i:i + 50])
        created += len(resp.get("successful", {}))
    log.info("Zotero: %d개 항목 추가.", created)
    return created
