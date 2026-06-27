"""시작판 백필 — profile.year_from ~ 현재 + 고전 canon. 1회 수동 실행.

사용:
  python entrypoints/backfill.py                 # 전체
  python entrypoints/backfill.py --limit 20      # 축소 dry-run(랭킹 후보 20편)
  python entrypoints/backfill.py --limit 20 --skip-llm   # Claude 미사용(무료 검증)
"""
from __future__ import annotations

import argparse

import _common  # noqa: F401  (경로 부트스트랩)

from paperarchive import config, pipeline
from paperarchive.state import load_seen, save_seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-llm", action="store_true")
    args = ap.parse_args()

    profile = config.load_profile()
    canon = config.load_canon()
    seen = load_seen()

    entries, processed = pipeline.run(
        profile,
        canon=canon,
        year_from=profile.get("year_from", 2013),
        seen=seen,
        limit=args.limit,
        skip_llm=args.skip_llm,
    )
    print(f"\n=== 백필: {len(entries)}편 선정 ===")

    _common.route(entries, telegram_on=False, export_label="backfill_" + _common.today_tag())

    save_seen(seen | processed)
    print(f"✓ seen 갱신: {len(seen | processed)}개")


if __name__ == "__main__":
    main()
