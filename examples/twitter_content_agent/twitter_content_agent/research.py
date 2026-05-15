"""Research helpers for the Twitter/X content sample.

The default path is deterministic so Eagle Eval can run in CI without network
or provider credentials. Developers can refresh the JSON snapshot manually when
they want the sample to reflect newer news.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RESEARCH_PATH = Path(__file__).with_name("latest_genai_updates.json")


def load_research_brief(path: Path | None = None) -> dict[str, Any]:
    """Load the latest curated GenAI research snapshot."""
    research_path = path or RESEARCH_PATH
    return json.loads(research_path.read_text(encoding="utf-8"))


def top_updates(limit: int = 3, path: Path | None = None) -> list[dict[str, Any]]:
    """Return the most useful updates for the sample post."""
    brief = load_research_brief(path)
    items = list(brief.get("items", []))
    items.sort(key=lambda item: item.get("published_at", ""), reverse=True)
    selected = []
    seen_providers = set()
    for item in items:
        provider = item.get("provider")
        if provider in seen_providers:
            continue
        selected.append(item)
        seen_providers.add(provider)
        if len(selected) >= limit:
            return selected

    for item in items:
        if item not in selected:
            selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def research_context(limit: int = 3, path: Path | None = None) -> str:
    """Format research items for an SDK prompt."""
    lines = []
    for index, item in enumerate(top_updates(limit=limit, path=path), start=1):
        lines.append(
            f"{index}. {item['provider']} ({item['published_at']}): "
            f"{item['title']} - {item['summary']} Source: {item['url']}"
        )
    return "\n".join(lines)


def source_payload(limit: int = 3, path: Path | None = None) -> list[dict[str, str]]:
    """Return source metadata for Eagle Eval reports."""
    return [
        {
            "provider": str(item["provider"]),
            "title": str(item["title"]),
            "published_at": str(item["published_at"]),
            "url": str(item["url"]),
        }
        for item in top_updates(limit=limit, path=path)
    ]
