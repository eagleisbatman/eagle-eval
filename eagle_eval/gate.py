"""Quality gate: automated checks plus model-scored review on synthetic data."""

import json
import logging
import time
from pathlib import Path

from eagle_eval.file_io import atomic_write_json

log = logging.getLogger(__name__)


def run_quality_gate(config: dict, data_dir: Path, dry_run: bool = False, verbose: bool = False) -> dict:
    """Run quality checks on all generated conversations."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    threshold = config["test_cases"].get("quality_threshold", 3.5)
    from eagle_eval.providers import infer_provider
    from eagle_eval.quality_review import review_conversation

    scorer = config["scoring"].get("scorer") or infer_provider(config["scoring"]["scorer_model"])
    scorer_model = config["scoring"]["scorer_model"]
    domain = config["domain"]
    persona = config.get("user_persona", "user")

    conversations = _load_all_conversations(data_dir)
    if not conversations:
        return {"total": 0, "passed": 0, "flagged": 0, "failed": 0, "per_language": {}}

    results = {"total": len(conversations), "passed": 0, "flagged": 0, "failed": 0, "per_language": {}}
    quality_scores = {}

    for conv_path, conv in conversations:
        conv_id = conv.get("conversation_id", conv_path.stem)
        lang = conv.get("language", "unknown")

        if lang not in results["per_language"]:
            results["per_language"][lang] = {"total": 0, "passed": 0, "flagged": 0, "failed": 0, "scores": []}
        results["per_language"][lang]["total"] += 1

        # Automated checks
        auto_issues = _auto_checks(conv)
        if auto_issues:
            log.info(f"{conv_id}: auto-check issues: {auto_issues}")

        # LLM quality review
        if dry_run:
            score = {"overall": 4.0, "naturalness": 4, "topic_coverage": 4, "difficulty_match": 4, "language_quality": 4, "issues": "dry run"}
        else:
            score = review_conversation(conv, scorer, scorer_model, domain, persona)

        if score is None:
            score = {"overall": 0, "issues": "LLM review failed"}

        overall = score.get("overall", 0)
        quality_scores[conv_id] = score
        results["per_language"][lang]["scores"].append(overall)

        # Classify
        if overall >= threshold:
            results["passed"] += 1
            results["per_language"][lang]["passed"] += 1
            conv["quality_score"] = overall
            conv["quality_status"] = "passed"
        elif overall >= threshold - 1.0:
            results["flagged"] += 1
            results["per_language"][lang]["flagged"] += 1
            conv["quality_score"] = overall
            conv["quality_status"] = "flagged"
        else:
            results["failed"] += 1
            results["per_language"][lang]["failed"] += 1
            conv["quality_score"] = overall
            conv["quality_status"] = "failed"

        # Write quality score back into the conversation file unless this is a preview.
        if not dry_run:
            atomic_write_json(conv_path, conv)

        log.info(f"{conv_id}: overall={overall:.1f} status={conv['quality_status']}")
        time.sleep(0.3)

    # Compute per-language averages
    for lang, stats in results["per_language"].items():
        scores = stats.pop("scores")
        stats["avg_quality"] = sum(scores) / len(scores) if scores else 0

    return results


def _load_all_conversations(data_dir: Path) -> list[tuple[Path, dict]]:
    """Load all conversation JSON files from data/synthetic/<lang>/."""
    conversations = []
    for json_file in sorted(data_dir.rglob("*.json")):
        if json_file.name in ("manifest.json", "quality_report.json"):
            continue
        try:
            conv = json.loads(json_file.read_text())
            if "conversation_turns" in conv:
                conversations.append((json_file, conv))
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Skipping {json_file}: {e}")
    return conversations


def _auto_checks(conv: dict) -> list[str]:
    """Run fast automated checks. Returns list of issues."""
    issues = []
    turns = conv.get("conversation_turns", [])

    if len(turns) < 3:
        issues.append(f"too few turns ({len(turns)})")

    # Check for empty turns
    empty = sum(1 for t in turns if not t.get("content", "").strip())
    if empty > 0:
        issues.append(f"{empty} empty turns")

    # Check for exact duplicates
    contents = [t.get("content", "") for t in turns]
    if len(contents) != len(set(contents)):
        issues.append("duplicate turns detected")

    # Check all turns have role=user
    non_user = [t for t in turns if t.get("role") != "user"]
    if non_user:
        issues.append(f"{len(non_user)} turns with role != 'user'")

    # Language detection (fast check on concatenated text)
    try:
        from langdetect import detect
        combined = " ".join(t.get("content", "") for t in turns[:3])
        if len(combined) > 30:
            detected = detect(combined)
            expected = conv.get("language", "")
            if detected.split("-")[0] != expected.split("-")[0]:
                issues.append(f"language mismatch: expected {expected}, detected {detected}")
    except Exception:
        pass

    return issues
