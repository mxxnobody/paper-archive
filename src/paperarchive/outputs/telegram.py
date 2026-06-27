"""텔레그램 Bot API 알림 — 주간 신규 논문 하이라이트.

환경변수: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
4096자 제한을 고려해 상위 N편만 요약하고 나머지는 HTML 링크로 안내.
"""
from __future__ import annotations

import logging
import os

import httpx

from ..record import Entry

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 4000  # 4096 안전 마진


def _esc(text: str) -> str:
    """HTML parse_mode용 최소 이스케이프."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message(entries: list[Entry], highlight_n: int, site_url: str | None) -> str:
    if not entries:
        return "📭 이번 주 새로운 관련 논문이 없습니다."
    head = f"📚 <b>이번 주 신규 논문 {len(entries)}편</b> (상위 {min(highlight_n, len(entries))}편 요약)\n"
    parts = [head]
    for i, e in enumerate(entries[:highlight_n], 1):
        p = e.paper
        title = _esc(p.title)
        link = p.url or ""
        block = (
            f"\n<b>{i}. {title}</b>\n"
            f"<i>{_esc(p.venue or 'NA')} ({p.year or 'NA'}) · 관련도 {e.scored.relevance}</i>\n"
            f"{_esc(e.summary.summary)}\n"
        )
        if link:
            block += f'🔗 <a href="{_esc(link)}">원문</a>\n'
        parts.append(block)
    if site_url:
        parts.append(f"\n📖 전체 보기: {_esc(site_url)}")
    msg = "".join(parts)
    if len(msg) > MAX_LEN:
        msg = msg[:MAX_LEN] + "…"
    return msg


def send(entries: list[Entry], highlight_n: int = 8, site_url: str | None = None) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        log.info("텔레그램 미설정 — 발송 건너뜀.")
        return False
    text = build_message(entries, highlight_n, site_url)
    try:
        r = httpx.post(
            API.format(token=token),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30.0,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("텔레그램 발송 실패: %s", e)
        return False
    log.info("텔레그램 발송 완료.")
    return True
