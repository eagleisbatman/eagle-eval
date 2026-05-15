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
        "## Scores",
        "",
        "| Language | Metric | Score |",
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
