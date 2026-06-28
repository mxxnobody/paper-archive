"""Zotero Web API 푸시 — read/write API 키로 지정 컬렉션에 항목 + 자식 노트 적재.

요약·비평은 부모 item의 extra가 아니라 **child note(자식 노트)**로 넣는다.
환경변수: ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_COLLECTION_KEY
미설정 시 조용히 건너뜀(로컬 실행 편의).
"""
from __future__ import annotations

import logging
import os

from ..record import Entry

log = logging.getLogger(__name__)

NOTE_TAG = "auto-summary"   # 재실행 시 자식 노트 갱신 식별용
TIER_SUB_NAMES = {"Tier 1", "Tier 2", "Tier 3", "Foundational"}  # 정리(삭제) 대상


def get_zotero():
    """(zot, collection_key) 반환. 미설정/미설치면 (None, None)."""
    api_key = os.environ.get("ZOTERO_API_KEY")
    user_id = os.environ.get("ZOTERO_USER_ID")
    collection_key = os.environ.get("ZOTERO_COLLECTION_KEY") or None
    if not (api_key and user_id):
        log.info("Zotero 미설정 — 건너뜀.")
        return None, None
    try:
        from pyzotero import zotero
    except ImportError:
        log.warning("pyzotero 미설치 — 건너뜀.")
        return None, None
    return zotero.Zotero(user_id, "user", api_key), collection_key


def _existing_dois(zot, collection_key: str | None) -> set[str]:
    dois: set[str] = set()
    try:
        items = (
            zot.everything(zot.collection_items_top(collection_key))
            if collection_key else zot.everything(zot.top())
        )
        for it in items:
            doi = (it.get("data", {}).get("DOI") or "").lower()
            if doi:
                dois.add(doi)
    except Exception as e:  # noqa: BLE001
        log.debug("Zotero 기존 DOI 조회 실패: %s", e)
    return dois


def _parent_item(zot, e: Entry, collection_key: str | None) -> dict:
    p = e.paper
    t = zot.item_template("journalArticle")
    t["title"] = p.title
    t["creators"] = [{"creatorType": "author", "name": a} for a in p.authors] \
        or [{"creatorType": "author", "name": ""}]
    t["publicationTitle"] = p.venue or ""
    t["date"] = str(p.year or "")
    t["DOI"] = p.doi or ""
    t["url"] = p.url or ""
    t["abstractNote"] = p.abstract or ""
    tags = [{"tag": c} for c in p.concepts[:6]]
    if e.scored.is_canon:
        tags.append({"tag": "canon"})
    tags.append({"tag": f"relevance:{e.scored.relevance}"})
    t["tags"] = tags
    t["extra"] = f"관련도 {e.scored.relevance}"
    if collection_key:
        t["collections"] = [collection_key]
    return t


def build_note_html(e: Entry) -> str:
    su = e.summary
    rows = [f"<p><b>요약</b>: {su.summary}</p>"]
    if su.key_result:
        rows.append(f"<p><b>핵심 결과</b>: {su.key_result}</p>")
    if su.dependent_var:
        rows.append(f"<p><b>종속변수</b>: {su.dependent_var}</p>")
    if su.independent_var:
        rows.append(f"<p><b>독립변수</b>: {su.independent_var}</p>")
    if su.method:
        rows.append(f"<p><b>방법</b>: {su.method}</p>")
    if su.caveats:
        rows.append(f"<p><b>⚠️ 유의점</b>: {su.caveats}</p>")
    if e.scored.reason:
        rows.append(f"<p><b>선정 이유</b>: {e.scored.reason}</p>")
    return "".join(rows)


def _note_item(zot, parent_key: str, e: Entry) -> dict:
    n = zot.item_template("note")
    n["parentItem"] = parent_key
    n["note"] = build_note_html(e)
    n["tags"] = [{"tag": NOTE_TAG}]
    return n


def _create_batched(zot, items: list[dict]) -> list[dict]:
    """50개씩 생성, 성공한 item dict들을 제출 순서대로 반환."""
    created: list[dict] = []
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        resp = zot.create_items(chunk)
        succ = resp.get("successful", {})
        # 인덱스 순으로 정렬해 제출 순서와 매칭
        for idx in sorted(succ, key=lambda k: int(k)):
            created.append(succ[idx])
    return created


def push(entries: list[Entry]) -> int:
    """신규 entry를 부모 item + 자식 노트로 추가. 추가된 부모 수 반환."""
    zot, collection_key = get_zotero()
    if zot is None:
        return 0
    existing = _existing_dois(zot, collection_key)

    new_entries, parents = [], []
    for e in entries:
        if e.paper.doi and e.paper.doi.lower() in existing:
            continue
        new_entries.append(e)
        parents.append(_parent_item(zot, e, collection_key))
    if not parents:
        log.info("Zotero: 추가할 신규 항목 없음.")
        return 0

    created = _create_batched(zot, parents)
    # 부모 키와 entry 매칭(제출 순서 동일) → 자식 노트 생성
    notes = []
    for e, item in zip(new_entries, created):
        key = item.get("key") or item.get("data", {}).get("key")
        if key:
            notes.append(_note_item(zot, key, e))
    if notes:
        _create_batched(zot, notes)
    log.info("Zotero: 부모 %d개 + 노트 %d개 추가.", len(created), len(notes))
    return len(created)


def tier_callnumbers(store: list[dict]) -> dict:
    """store(tier 부여됨)로부터 {doi(소문자): callNumber} 매핑 계산.

    tier별 그룹화 후 relevance 내림차순 순위 → 'T{code}-{rank:03d}'.
    code: 1/2/3, Foundational은 'F'(ASCII상 T3 뒤로 정렬). 순수 함수.
    """
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for d in store:
        groups[d.get("tier")].append(d)
    out: dict = {}
    for tier, ds in groups.items():
        ranked = sorted((d for d in ds if d.get("doi")),
                        key=lambda d: (d.get("relevance", 0), d.get("cited_by", 0)),
                        reverse=True)
        code = "F" if tier == "F" else str(tier)
        for i, d in enumerate(ranked, 1):
            out[d["doi"].lower()] = f"T{code}-{i:03d}"
    return out


def delete_tier_subcollections(zot, parent: str) -> int:
    """기존 Tier/Foundational 서브컬렉션 제거(항목은 부모에 남음). 삭제 수 반환."""
    removed = 0
    for c in zot.everything(zot.collections_sub(parent)):
        if c["data"]["name"] in TIER_SUB_NAMES:
            zot.delete_collection(c)
            removed += 1
    return removed


def retier(store: list[dict]) -> int:
    """store의 tier에 맞춰 각 항목 Call Number를 설정(차분). 변경 항목 수 반환."""
    zot, parent = get_zotero()
    if zot is None or parent is None:
        return 0
    cn = tier_callnumbers(store)
    items = zot.everything(zot.collection_items_top(parent))
    changed = []
    for it in items:
        doi = (it["data"].get("DOI") or "").lower()
        want = cn.get(doi)
        if want and it["data"].get("callNumber") != want:
            it["data"]["callNumber"] = want
            changed.append(it)
    for i in range(0, len(changed), 50):  # 항목별 version → 배치 충돌 없음
        zot.update_items(changed[i:i + 50])
    log.info("Zotero retier: Call Number %d개 갱신.", len(changed))
    return len(changed)
