"""Local dataset storage helpers."""

from __future__ import annotations

import json
from pathlib import Path


def write_local_datasets(
    config: dict,
    lang_codes: list[str],
    data_dir: Path,
    recreate: bool = False,
) -> dict:
    """Write local dataset JSON files from quality-gated conversations."""
    project_dir = data_dir.expanduser().resolve().parent.parent
    datasets_dir = local_results_dir(config, project_dir) / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    results = {"datasets": {}, "total_items": 0}
    for lang_code in lang_codes:
        lang_dir = data_dir / lang_code
        items = [_conversation_to_item(lang_code, conv) for conv in _load_passed_conversations(lang_dir)]
        dataset_path = datasets_dir / f"{lang_code}_conversations.json"
        if dataset_path.exists() and not recreate:
            existing = json.loads(dataset_path.read_text(encoding="utf-8"))
            existing.extend(items)
            items = existing
        dataset_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        results["datasets"][str(dataset_path)] = len(items)
        results["total_items"] += len(items)
    return results


def local_results_dir(config: dict, project_dir: Path) -> Path:
    """Resolve the configured local results directory."""
    local_config = config.get("results", {}).get("local", {})
    configured = Path(str(local_config.get("directory", "data/results"))).expanduser()
    if configured.is_absolute():
        return configured
    return project_dir.expanduser().resolve() / configured


def load_items(project_dir: Path, config: dict, lang_code: str) -> list[dict]:
    dataset_path = local_results_dir(config, project_dir) / "datasets" / f"{lang_code}_conversations.json"
    if dataset_path.exists():
        return json.loads(dataset_path.read_text(encoding="utf-8"))

    lang_dir = project_dir / "data" / "synthetic" / lang_code
    return [_conversation_to_item(lang_code, conv) for conv in _load_passed_conversations(lang_dir)]


def _load_passed_conversations(lang_dir: Path) -> list[dict]:
    conversations = []
    if not lang_dir.exists():
        return conversations

    for json_file in sorted(lang_dir.glob("*.json")):
        try:
            conv = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if conv.get("quality_status", "passed") in ("passed", "flagged"):
            conversations.append(conv)
    return conversations


def _conversation_to_item(lang_code: str, conv: dict) -> dict:
    turns = conv.get("conversation_turns", [])
    expected_output = {
        "expected_topics": conv.get("topic_tags", [conv.get("primary_topic", "general")]),
        "expected_language": lang_code,
        "min_turns_responded": max(1, int(len(turns) * 0.8)),
        "scenario": conv.get("scenario"),
        "expected_next_action": conv.get("expected_next_action"),
        "required_clarification_slots": conv.get("required_clarification_slots", []),
        "resolution_goal": conv.get("resolution_goal"),
    }
    expected_output.update(conv.get("expected_output") or {})
    return {
        "input": {"language": lang_code, "conversation_turns": turns},
        "expected_output": expected_output,
        "metadata": {
            "language": lang_code,
            "language_name": conv.get("language_name", lang_code),
            "conversation_id": conv.get("conversation_id", "unknown"),
            "primary_topic": conv.get("primary_topic", "general"),
            "scenario": conv.get("scenario"),
            "expected_next_action": conv.get("expected_next_action"),
            "difficulty": conv.get("difficulty_actual", conv.get("difficulty_requested", "medium")),
            "quality_score": conv.get("quality_score"),
            "generated_by": conv.get("generated_by", "unknown"),
        },
    }
