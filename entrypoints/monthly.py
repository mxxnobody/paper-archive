"""월간 종합 — 최근 1년치를 다시 훑어 누락분을 HTML/Zotero/RIS에 보강(텔레그램 없음)."""
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
        year_from=cur_year - 1,
        seen=seen,
    )
    print(f"\n=== 월간 종합: {len(entries)}편 보강 ===")

    _common.route(profile, entries, telegram_on=False,
                  export_label="monthly_" + _common.today_tag())

    save_seen(seen | processed)


if __name__ == "__main__":
    main()
