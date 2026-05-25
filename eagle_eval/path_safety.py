"""Path and filename guardrails for user-controlled config values."""

from __future__ import annotations

import re
from pathlib import Path

_LANGUAGE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_UNSAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def validate_language_code(value: str) -> str:
    """Return a normalized language code or raise ValueError."""
    normalized = str(value).strip().lower()
    if not _LANGUAGE_CODE_RE.fullmatch(normalized):
        raise ValueError(f"Invalid language code '{value}'. Use letters, numbers, '_' or '-'.")
    return normalized


def safe_filename_part(value: object, fallback: str) -> str:
    """Convert a display value into a safe single filename segment."""
    cleaned = _UNSAFE_FILENAME_RE.sub("-", str(value).strip()).strip(".-")
    return cleaned or fallback


def project_relative_directory(project_dir: Path, configured: object, label: str) -> Path:
    """Resolve a configured directory and require it to stay inside the project."""
    root = project_dir.expanduser().resolve()
    raw_path = Path(str(configured)).expanduser()
    resolved = raw_path.resolve() if raw_path.is_absolute() else (root / raw_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the eval project: {configured}") from exc
    return resolved
