"""Load Eagle Eval environment files without adding a dotenv dependency."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnvFileStatus:
    path: Path
    keys: tuple[str, ...]


def load_env_files(project_root: Path, home_dir: Path | None = None) -> list[EnvFileStatus]:
    """Load global and project env files, with project files taking precedence."""
    statuses = []
    for path in env_file_candidates(project_root, home_dir):
        if not path.exists():
            continue
        values = parse_env_file(path)
        for key, value in values.items():
            os.environ[key] = value
        statuses.append(EnvFileStatus(path=path, keys=tuple(values)))
    return statuses


def env_file_candidates(project_root: Path, home_dir: Path | None = None) -> tuple[Path, ...]:
    home = (home_dir or Path.home()).expanduser().resolve()
    root = project_root.expanduser().resolve()
    return (
        home / ".eagle-eval" / ".env",
        root / ".env",
        root / ".env.eagle-eval",
    )


def parse_env_file(path: Path) -> dict[str, str]:
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_line(raw_line)
        if parsed:
            key, value = parsed
            values[key] = value
    return values


def _parse_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
        return None
    return key, _clean_value(value.strip())


def _clean_value(value: str) -> str:
    if not value:
        return ""
    quote = value[0]
    if quote in {"'", '"'}:
        end = value.find(quote, 1)
        return value[1:end] if end != -1 else value[1:]
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value
