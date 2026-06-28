"""일회성 재정비 — 기존 아카이브를 새 임계값/요약으로 정리.

- site/data.json 의 모든 항목을 새 summarize()로 재요약(저장된 abstract 사용)
- relevance >= threshold 만 남기고 상위 retidy_max 편으로 컷(동점 인용수)
- data.json/HTML/RIS 재작성
- Zotero 컬렉션을 비우고 유지분만 부모 item + 자식 노트로 재적재

주의: Zotero 삭제는 ZOTERO_COLLECTION_KEY 컬렉션 한정. 실행 전 수량을 출력한다.
"""
from __future__ import annotations

import _common  # noqa: F401

from paperarchive import config
from paperarchive.outputs import html_site, ris, zotero
from paperarchive.record import Entry
from paperarchive.summarize import summarize


def main():
    profile = config.load_profile()
    rcfg = profile.get("ranking", {})
    threshold = rcfg.get("relevance_threshold", 80)
    cap = rcfg.get("retidy_max", 200)
    site_dir = _common.ROOT / "site"

    store = html_site.load_store(site_dir)
    print(f"현재 아카이브: {len(store)}편")
    if not store:
        print("data.json 비어 있음 — 중단")
        return

    entries = [Entry.from_dict(d) for d in store]
    for e in entries:               # 새 형식으로 재요약
        e.summary = summarize(e.scored)

    kept = [e for e in entries if e.scored.relevance >= threshold or e.scored.is_canon]
    kept.sort(key=lambda e: (e.scored.relevance, e.paper.cited_by), reverse=True)
    kept = kept[:cap]
    print(f"유지 대상: {len(kept)}편 (임계값 {threshold}, 상한 {cap})")

    # data.json + HTML 재작성 (기존 store는 버리고 kept로 교체)
    new_store = html_site.merge([], kept)
    html_site.save_store(site_dir, new_store)
    html_site.render(site_dir, new_store, _common.now_kst_str())
    print(f"✓ data.json/HTML 재작성: {len(new_store)}편")

    ris.write_ris(kept, _common.ROOT / "exports" / ("retidy_" + _common.today_tag() + ".ris"))
    print("✓ RIS 백업")

    # Zotero: 컬렉션 비우고 유지분 재적재(부모 + 자식 노트)
    zot, coll = zotero.get_zotero()
    if zot and coll:
        total = len(zot.everything(zot.collection_items_top(coll)))
        print(f"Zotero 컬렉션 기존 {total}편 → 전부 삭제 후 {len(kept)}편 재적재")
        # 배치마다 재조회(삭제로 라이브러리 버전이 바뀌어 stale-version 412 방지)
        removed = 0
        while True:
            batch = zot.collection_items_top(coll, limit=50)
            if not batch:
                break
            zot.delete_item(batch)
            removed += len(batch)
        print(f"  삭제 완료: {removed}편")
        n = zotero.push(kept)
        print(f"✓ Zotero 재적재: {n}편 (+ 자식 노트)")
    else:
        print("Zotero 미설정 — 건너뜀")


if __name__ == "__main__":
    main()
