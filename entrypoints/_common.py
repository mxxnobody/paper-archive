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


def site_url() -> str | None:
    return os.environ.get("SITE_URL")  # 예: https://user.github.io/paper-archive/


def route(entries, *, telegram_on: bool, highlight_n: int = 8, export_label: str = ""):
    """엔트리를 HTML/Zotero/RIS(/Telegram)로 전달."""
    from paperarchive.outputs import html_site, ris, telegram, zotero

    site_dir = ROOT / "site"
    html_site.update_site(site_dir, entries, now_kst_str())
    print(f"✓ HTML 갱신: {site_dir/'index.html'} (총 {len(html_site.load_store(site_dir))}편)")

    pushed = zotero.push(entries)
    print(f"✓ Zotero 추가: {pushed}편")

    if entries:
        exports = ROOT / "exports"
        label = export_label or today_tag()
        ris_path = ris.write_ris(entries, exports / f"{label}.ris")
        print(f"✓ RIS export: {ris_path}")

    if telegram_on:
        ok = telegram.send(entries, highlight_n=highlight_n, site_url=site_url())
        print(f"✓ 텔레그램: {'발송' if ok else '건너뜀'}")
