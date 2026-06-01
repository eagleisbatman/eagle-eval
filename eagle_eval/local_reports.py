"""Markdown report rendering for local eval runs."""

from __future__ import annotations


def markdown_report(report: dict) -> str:
    lines = [
        f"# Eagle Eval Local Run: {report['run_name']}",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Items: `{len(report['items'])}`",
        f"- Model scorers included: `{report['settings']['include_model_scorers']}`",
        "",
        "## Goal Summary",
        "",
        *_goal_summary_lines(report.get("summary", {})),
        "",
        "## Scores",
        "",
        "| Language | Metric | Mean |",
        "| --- | --- | ---: |",
    ]
    for language, scores in report["scores"].items():
        if not scores:
            lines.append(f"| {language} | no_scores | 0.000 |")
        for metric, score in scores.items():
            lines.append(f"| {language} | {metric} | {score:.3f} |")

    lines.extend(["", "## Items", ""])
    for item in report["items"]:
        lines.append(f"### {item['metadata'].get('conversation_id', 'unknown')}")
        lines.append("")
        for evaluation in item["evaluations"]:
            value = evaluation.get("value")
            value_text = f"{float(value):.3f}" if value is not None else "n/a"
            lines.append(f"- `{evaluation['name']}`: `{value_text}` {evaluation.get('comment', '')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _goal_summary_lines(summary: dict) -> list[str]:
    if not summary:
        return ["No goal summary available."]
    goal = summary.get("goal_achievement", {})
    judge = summary.get("goal_achievement_judge", {})
    action = summary.get("next_action_match", {})
    lines = [
        f"- Goal achievement: {_stat(goal, 'met')}",
        f"- Next-action match: {_stat(action, 'matched')}",
    ]
    if judge.get("scored"):
        lines.append(f"- Model-judged goal achievement: {_stat(judge, 'met')}")
    if summary.get("scenarios"):
        lines.extend(["", "| Scenario | Items | Goals Met | Next Actions Matched |", "| --- | ---: | ---: | ---: |"])
        for scenario, data in sorted(summary["scenarios"].items()):
            g = data["goal_achievement"]
            a = data["next_action_match"]
            lines.append(f"| {scenario} | {data['total_items']} | {g.get('met', 0)}/{g.get('scored', 0)} | {a.get('matched', 0)}/{a.get('scored', 0)} |")
    if summary.get("failed_cases"):
        lines.extend(["", "Failed goal cases:"])
        for case in summary["failed_cases"][:10]:
            lines.append(f"- `{case['conversation_id']}` ({case['scenario']}): {case['reason']}")
    if summary.get("recommended_fixes"):
        lines.extend(["", "Recommended fixes:"])
        lines.extend(f"- {fix}" for fix in summary["recommended_fixes"])
    return lines


def _rate(bucket: dict) -> str:
    rate = bucket.get("rate")
    return "n/a" if rate is None else f"{rate * 100:.0f}%"


def _stat(bucket: dict, positive_key: str) -> str:
    mean = bucket.get("mean")
    mean_text = "n/a" if mean is None else f"{mean:.3f}"
    return f"mean `{mean_text}` · `{bucket.get(positive_key, 0)}/{bucket.get('scored', 0)}` ≥0.5 ({_rate(bucket)})"
