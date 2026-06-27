"""저장된 아카이브(site/data.json) 전체를 Zotero로 푸시.

Zotero를 나중에 연결했거나 컬렉션을 새로 만들었을 때, 기존 아카이브를
한 번에 적재하기 위한 일회성 도구. 중복 DOI는 zotero.push가 알아서 건너뜀.
"""
from __future__ import annotations

import json

import _common  # noqa: F401

from paperarchive.outputs import zotero
from paperarchive.outputs.html_site import DATA_FILE
from paperarchive.record import Entry


def main():
    data_path = _common.ROOT / "site" / DATA_FILE
    store = json.loads(data_path.read_text(encoding="utf-8"))
    entries = [Entry.from_dict(d) for d in store]
    print(f"아카이브 {len(entries)}편 → Zotero 푸시 시작")
    pushed = zotero.push(entries)
    print(f"✓ Zotero 추가: {pushed}편 (중복 제외)")


if __name__ == "__main__":
    main()
