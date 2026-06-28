"""엔트리포인트 공용 — 경로 부트스트랩, 출력 라우팅."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# src/ 를 import 경로에 추가 (workflow/로컬 공통)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def now_kst_str() -> str:
    # KST = UTC+9
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


def today_tag() -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y%m%d")


def today_iso() -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")


def site_url() -> str | None:
    return os.environ.get("SITE_URL")  # 예: https://user.github.io/paper-archive/


def _weekly_url(date_tag: str) -> str | None:
    base = site_url()
    if not base:
        return None
    return f"{base.rstrip('/')}/weekly/{date_tag}.html"


def route(profile, entries, *, telegram_on: bool, highlight_n: int = 10,
          export_label: str = "", weekly_page: bool = False, date_tag: str = ""):
    """엔트리를 HTML(티어)/주간페이지/Zotero(티어 동기화)/RIS/Telegram로 전달."""
    from paperarchive.outputs import html_site, ris, telegram, zotero

    rcfg = profile.get("ranking", {})
    site_dir = ROOT / "site"

    # 누적 저장 + 티어 부여 + 메인 렌더 → 전체 store 반환
    store = html_site.update_site(site_dir, entries, now_kst_str(),
                                  tier1=rcfg.get("tier1_size", 25),
                                  tier2=rcfg.get("tier2_size", 75))
    print(f"✓ HTML 갱신: {site_dir/'index.html'} (총 {len(store)}편)")

    link = site_url()
    if weekly_page:
        wp = html_site.render_weekly(site_dir, entries, date_tag)
        link = _weekly_url(date_tag)
        print(f"✓ 주간 페이지: {wp}")

    pushed = zotero.push(entries)
    print(f"✓ Zotero 추가: {pushed}편")
    moved = zotero.retier(store)
    print(f"✓ Zotero 티어 동기화: {moved}개 이동")

    if entries:
        ris_path = ris.write_ris(entries, ROOT / "exports" / f"{export_label or today_tag()}.ris")
        print(f"✓ RIS export: {ris_path}")

    if telegram_on:
        ok = telegram.send(entries, highlight_n=highlight_n, site_url=link)
        print(f"✓ 텔레그램: {'발송' if ok else '건너뜀'}")
