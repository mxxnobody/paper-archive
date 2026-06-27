"""RIS 서지 export — Zotero 백업/수동 임포트용."""
from __future__ import annotations

from pathlib import Path

from ..record import Entry


def _ris_record(e: Entry) -> str:
    p = e.paper
    lines = ["TY  - JOUR"]
    for a in p.authors:
        lines.append(f"AU  - {a}")
    lines.append(f"TI  - {p.title}")
    if p.venue:
        lines.append(f"JO  - {p.venue}")
    if p.year:
        lines.append(f"PY  - {p.year}")
    if p.abstract:
        lines.append(f"AB  - {p.abstract}")
    if p.doi:
        lines.append(f"DO  - {p.doi}")
    if p.url:
        lines.append(f"UR  - {p.url}")
    # 한국어 요약·관련도를 노트로
    note = f"[관련도 {e.scored.relevance}] {e.summary.summary}"
    lines.append(f"N1  - {note}")
    lines.append("ER  - ")
    return "\n".join(lines)


def write_ris(entries: list[Entry], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(_ris_record(e) for e in entries) + "\n"
    path.write_text(content, encoding="utf-8")
    return path
