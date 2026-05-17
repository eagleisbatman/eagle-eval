"""Goal-first summary helpers for local reports."""

from __future__ import annotations


def build_goal_summary(items: list[dict]) -> dict:
    summary = {
        "total_items": len(items),
        "goal_achievement": _metric_bucket("met"),
        "next_action_match": _metric_bucket("matched"),
        "scenarios": {},
        "failed_cases": [],
        "recommended_fixes": [],
    }
    for item in items:
        scenario = _scenario(item)
        _ensure_scenario(summary, scenario)
        _record_metric(summary, scenario, "goal_achievement", "met", item)
        _record_metric(summary, scenario, "next_action_match", "matched", item)
        _record_failure(summary, item, scenario)

    _finalize(summary["goal_achievement"], "met")
    _finalize(summary["next_action_match"], "matched")
    for scenario_bucket in summary["scenarios"].values():
        _finalize(scenario_bucket["goal_achievement"], "met")
        _finalize(scenario_bucket["next_action_match"], "matched")
    summary["recommended_fixes"] = _recommended_fixes(summary["failed_cases"])
    return summary


def _record_metric(summary: dict, scenario: str, metric: str, positive_key: str, item: dict):
    value = _evaluation_value(item, metric)
    for bucket in (summary[metric], summary["scenarios"][scenario][metric]):
        if value is None:
            continue
        bucket["scored"] += 1
        if value >= 0.5:
            bucket[positive_key] += 1


def _record_failure(summary: dict, item: dict, scenario: str):
    evaluation = _evaluation(item, "goal_achievement")
    value = evaluation.get("value") if evaluation else None
    if value is None or value >= 0.5:
        return
    expected = item.get("expected_output", {})
    metadata = item.get("metadata", {})
    summary["failed_cases"].append(
        {
            "conversation_id": metadata.get("conversation_id", "unknown"),
            "language": metadata.get("language", item.get("language", "unknown")),
            "scenario": scenario,
            "expected_next_action": metadata.get("expected_next_action") or expected.get("expected_next_action"),
            "resolution_goal": expected.get("resolution_goal"),
            "reason": evaluation.get("comment", ""),
        }
    )


def _ensure_scenario(summary: dict, scenario: str):
    if scenario not in summary["scenarios"]:
        summary["scenarios"][scenario] = {
            "total_items": 0,
            "goal_achievement": _metric_bucket("met"),
            "next_action_match": _metric_bucket("matched"),
        }
    summary["scenarios"][scenario]["total_items"] += 1


def _metric_bucket(positive_key: str) -> dict:
    return {"scored": 0, positive_key: 0, "rate": None}


def _finalize(bucket: dict, positive_key: str):
    bucket["rate"] = round(bucket[positive_key] / bucket["scored"], 3) if bucket["scored"] else None


def _scenario(item: dict) -> str:
    expected = item.get("expected_output", {})
    metadata = item.get("metadata", {})
    return metadata.get("scenario") or expected.get("scenario") or "unknown"


def _evaluation(item: dict, name: str) -> dict | None:
    return next((evaluation for evaluation in item.get("evaluations", []) if evaluation.get("name") == name), None)


def _evaluation_value(item: dict, name: str) -> float | None:
    evaluation = _evaluation(item, name)
    value = evaluation.get("value") if evaluation else None
    return float(value) if value is not None else None


def _recommended_fixes(failed_cases: list[dict]) -> list[str]:
    scenarios = {case.get("scenario") for case in failed_cases}
    fixes = []
    if "missing_critical_context" in scenarios or "unclear_intent" in scenarios:
        fixes.append("Tune clarification behavior: ask focused questions for the minimum missing facts.")
    if "answerable_now" in scenarios:
        fixes.append("Tune direct-answer behavior: provide actionable answers when the query is already clear.")
    if "unsafe_or_high_risk" in scenarios:
        fixes.append("Tune escalation behavior: avoid unsafe advice and route high-risk cases to qualified support.")
    return fixes
