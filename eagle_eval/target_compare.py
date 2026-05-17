"""Compare orchestrated eval target results against sub-flow targets."""

from __future__ import annotations


def build_target_comparison(results: dict, orchestrator: str, sub_targets: list[str]) -> dict:
    """Build a compact cross-target comparison from run_experiment results."""
    target_stats = {name: _target_stats(result) for name, result in results.items()}
    orchestrator_stats = target_stats.get(orchestrator, {})
    gaps = []
    for target in sub_targets:
        gap = _goal_gap(orchestrator_stats, target_stats.get(target, {}))
        if gap is not None and gap < 0:
            gaps.append(
                {
                    "target": target,
                    "goal_achievement_delta": round(gap, 3),
                    "recommendation": f"Inspect orchestration around '{target}'; sub-flow is stronger than the orchestrated run.",
                }
            )
    return {
        "orchestrator": orchestrator,
        "sub_targets": sub_targets,
        "targets": target_stats,
        "gaps": gaps,
        "verdict": "needs_attention" if gaps else "aligned",
    }


def _target_stats(result: dict) -> dict:
    summary = result.get("summary") or {}
    scores = result.get("scores") or {}
    return {
        "items": summary.get("total_items"),
        "goal_achievement_rate": _first_rate(summary, scores, "goal_achievement"),
        "next_action_match_rate": _first_rate(summary, scores, "next_action_match"),
        "failed_cases": len(summary.get("failed_cases", [])),
    }


def _goal_gap(orchestrator: dict, sub_target: dict) -> float | None:
    orch_rate = orchestrator.get("goal_achievement_rate")
    sub_rate = sub_target.get("goal_achievement_rate")
    if orch_rate is None or sub_rate is None:
        return None
    return orch_rate - sub_rate


def _summary_rate(summary: dict, metric: str) -> float | None:
    bucket = summary.get(metric) or {}
    return bucket.get("rate")


def _first_rate(summary: dict, scores: dict, metric: str) -> float | None:
    summary_value = _summary_rate(summary, metric)
    return summary_value if summary_value is not None else _score_rate(scores, metric)


def _score_rate(scores: dict, metric: str) -> float | None:
    values = [
        float(lang_scores[metric])
        for lang_scores in scores.values()
        if isinstance(lang_scores, dict) and isinstance(lang_scores.get(metric), (int, float))
    ]
    return round(sum(values) / len(values), 3) if values else None
