"""주간 신규 알림 — 최근 논문을 텔레그램으로. HTML/Zotero/RIS에도 누적."""
from __future__ import annotations

from datetime import datetime, timezone

import _common  # noqa: F401

from paperarchive import config, pipeline
from paperarchive.state import load_seen, save_seen


def main():
    profile = config.load_profile()
    seen = load_seen()
    cur_year = datetime.now(timezone.utc).year

    entries, processed = pipeline.run(
        profile,
        canon=None,
        year_from=cur_year - 1,   # 연초 경계 대비 전년도부터, seen으로 중복 제거
        seen=seen,
    )
    print(f"\n=== 주간: {len(entries)}편 신규 ===")

    hn = profile.get("ranking", {}).get("weekly_highlight_n", 8)
    _common.route(entries, telegram_on=True, highlight_n=hn,
                  export_label="weekly_" + _common.today_tag())

    save_seen(seen | processed)


if __name__ == "__main__":
    main()
