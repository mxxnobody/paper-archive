"""주간 신규 알림 — 최근 논문 상위 N편만 텔레그램·Zotero·아카이브에 추가.

상한(weekly_max) 초과분은 seen에 기록하지 않아 다음 주 재경합(상위 N편 드립).
임계값 미달 후보는 seen에 기록해 재평가를 막는다.
"""
from __future__ import annotations

from datetime import datetime, timezone

import _common  # noqa: F401

from paperarchive import config, pipeline
from paperarchive.state import load_seen, save_seen


def main():
    profile = config.load_profile()
    rcfg = profile.get("ranking", {})
    weekly_max = rcfg.get("weekly_max", 20)
    highlight_n = rcfg.get("weekly_highlight_n", 10)
    seen = load_seen()
    cur_year = datetime.now(timezone.utc).year

    # entries: 임계값 이상, relevance 내림차순. processed: 평가한 전체 후보 key.
    entries, processed = pipeline.run(
        profile, canon=None, year_from=cur_year - 1, seen=seen,
    )

    delivered, seen_add = pipeline.weekly_selection(entries, processed, weekly_max)
    carried = len(entries) - len(delivered)

    print(f"\n=== 주간: 신규 {len(entries)}편 중 상위 {len(delivered)}편 전달"
          f"{f' (이월 {carried}편)' if carried else ''} ===")

    _common.route(delivered, telegram_on=True, highlight_n=highlight_n,
                  export_label="weekly_" + _common.today_tag())

    save_seen(seen | seen_add)


if __name__ == "__main__":
    main()
