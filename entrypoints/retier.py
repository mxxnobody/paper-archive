"""일회성 — 현재 아카이브에 티어 부여 + Zotero 서브컬렉션(Tier 1/2/3 + Foundational) 동기화."""
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

    moved = zotero.retier(store)
    print(f"✓ Zotero 서브컬렉션 동기화: {moved}개 이동")


if __name__ == "__main__":
    main()
