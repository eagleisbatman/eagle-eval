"""Small atomic file-write helpers."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp_path.write_text(content, encoding=encoding)
    temp_path.replace(path)


def atomic_write_json(path: Path, payload, *, ensure_ascii: bool = False) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=ensure_ascii), encoding="utf-8")
