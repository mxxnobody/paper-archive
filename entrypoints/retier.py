"""일회성 — 현재 아카이브에 티어 부여 + Zotero Call Number 정렬 코드 설정.

기존 Tier 서브컬렉션이 있으면 먼저 삭제하고 Call Number 방식으로 전환한다.
"""
from __future__ import annotations

from collections import Counter

import _common  # noqa: F401

from paperarchive import config
from paperarchive.outputs import html_site, zotero
from paperarchive.tiers import assign_tiers


def main():
    profile = config.load_profile()
    rcfg = profile.get("ranking", {})
    site_dir = _common.ROOT / "site"

    store = html_site.load_store(site_dir)
    if not store:
        print("data.json 비어 있음 — 중단")
        return
    assign_tiers(store, rcfg.get("tier1_size", 25), rcfg.get("tier2_size", 75))
    html_site.save_store(site_dir, store)
    html_site.render(site_dir, store, _common.now_kst_str())
    print(f"✓ 티어 부여: {len(store)}편 / 분포 {dict(Counter(d.get('tier') for d in store))}")

    # 기존 서브컬렉션 정리 후 Call Number 방식으로 전환
    zot, parent = zotero.get_zotero()
    if zot and parent:
        deleted = zotero.delete_tier_subcollections(zot, parent)
        print(f"✓ 기존 서브컬렉션 삭제: {deleted}개")
    moved = zotero.retier(store)
    print(f"✓ Zotero Call Number 설정: {moved}개")


if __name__ == "__main__":
    main()
