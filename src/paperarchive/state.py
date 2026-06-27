"""처리 이력(seen) 관리 — 같은 논문을 두 번 전달하지 않기 위함.

state/seen.json 에 처리한 논문 key(Paper.key())를 저장한다.
GitHub Actions에서는 실행 후 이 파일을 커밋해 이력을 유지한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from .sources.base import Paper

DEFAULT_PATH = Path("state/seen.json")


def load_seen(path: Path = DEFAULT_PATH) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("seen", []))


def save_seen(seen: set[str], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"seen": sorted(seen)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def filter_new(papers: list[Paper], seen: set[str]) -> list[Paper]:
    """아직 처리하지 않은 논문만 반환."""
    return [p for p in papers if p.key() not in seen]
