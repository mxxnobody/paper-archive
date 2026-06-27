"""config/*.yaml 로더."""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR = Path("config")


def load_profile(path: Path = CONFIG_DIR / "profile.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_canon(path: Path = CONFIG_DIR / "canon.yaml") -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("canon", [])
