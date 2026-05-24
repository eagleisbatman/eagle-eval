"""Small output helpers for the Eagle Eval CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click

BRAND_TAGLINE = "Goal-first eval runner for AI agents"


def log(msg, bold=False, fg=None):
    click.echo(click.style(msg, bold=bold, fg=fg))


def ok(msg):
    log(f"  ✓ {msg}", fg="green")


def warn(msg):
    log(f"  ⚠ {msg}", fg="yellow")


def err(msg):
    log(f"  ✗ {msg}", fg="red")


def banner():
    log("\n  Eagle Eval", bold=True, fg="cyan")
    log(f"  {BRAND_TAGLINE}", fg="cyan")
    log("")


def heading(msg):
    title = msg if msg.startswith("Eagle Eval") else f"Eagle Eval • {msg}"
    log(f"\n  {'─' * 46}", fg="cyan")
    log(f"  {title}", bold=True, fg="cyan")
    log(f"  {'─' * 46}", fg="cyan")


def pct(n, total):
    return f"{n / total * 100:.0f}%" if total else "0%"


def format_readiness_map(values: dict, ok_label: str, missing_label: str) -> str:
    return ", ".join(f"{name}={ok_label if ok else missing_label}" for name, ok in values.items())


def print_results_table(results: dict):
    _print_goal_summary(results.get("summary", {}))
    try:
        from tabulate import tabulate
    except ImportError:
        for lang, scores in results.get("scores", {}).items():
            log(f"  {lang}:")
            for metric, value in scores.items():
                log(f"    {metric}: {value:.3f}")
        return

    rows = [
        [lang, metric, f"{value:.3f}"]
        for lang, scores in results.get("scores", {}).items()
        for metric, value in scores.items()
    ]
    log(tabulate(rows, headers=["Language", "Metric", "Score"], tablefmt="rounded_grid"))


def _print_goal_summary(summary: dict):
    if not summary:
        return
    goal = summary.get("goal_achievement", {})
    judge = summary.get("goal_achievement_judge", {})
    action = summary.get("next_action_match", {})
    if goal.get("scored"):
        log(f"  Goal achievement: {goal.get('met', 0)}/{goal['scored']} ({_rate(goal)})", bold=True)
    if judge.get("scored"):
        log(f"  Model-judged goal achievement: {judge.get('met', 0)}/{judge['scored']} ({_rate(judge)})")
    if action.get("scored"):
        log(f"  Next-action match: {action.get('matched', 0)}/{action['scored']} ({_rate(action)})")
    if summary.get("failed_cases"):
        warn(f"Goal failures: {len(summary['failed_cases'])} case(s)")


def _rate(bucket: dict) -> str:
    rate = bucket.get("rate")
    return "n/a" if rate is None else f"{rate * 100:.0f}%"


def print_local_result_paths(results: dict):
    local_results = results.get("local_results")
    if not local_results:
        return
    log("\n  Local reports:")
    ok(f"JSON: {local_results['json']}")
    ok(f"Markdown: {local_results['markdown']}")
    log(f"  Items scored: {local_results['items']}")


def print_local_status(project_dir: Path, config: dict):
    from eagle_eval.local_datasets import local_results_dir

    results_dir = local_results_dir(config, project_dir)
    _print_datasets(results_dir / "datasets")
    _print_runs(results_dir / "runs")


def print_comparison_table(baseline_results: dict, candidate_results: dict, threshold: float):
    try:
        from tabulate import tabulate
    except ImportError:
        tabulate = None

    regressions = []
    rows = []
    for lang in baseline_results.get("scores", {}):
        if lang not in candidate_results.get("scores", {}):
            continue
        for metric in baseline_results["scores"][lang]:
            base = baseline_results["scores"][lang].get(metric, 0)
            candidate = candidate_results["scores"][lang].get(metric, 0)
            delta = candidate - base
            status = "✓" if delta >= -threshold else "⚠ REG"
            if delta < -threshold:
                regressions.append({"lang": lang, "metric": metric, "delta": delta})
            rows.append([lang, metric, f"{base:.3f}", f"{candidate:.3f}", f"{delta:+.3f}", status])

    if tabulate:
        log(tabulate(rows, headers=["Language", "Metric", "Baseline", "Candidate", "Delta", "Status"], tablefmt="rounded_grid"))
    else:
        for row in rows:
            log(f"  {row[0]:6s} {row[1]:25s} {row[2]:8s} {row[3]:8s} {row[4]:8s} {row[5]}")
    return regressions


def _print_datasets(datasets_dir: Path):
    if not datasets_dir.exists():
        warn("No local datasets. Run 'eagle-eval upload' or run directly from generated data.")
        return

    datasets = sorted(datasets_dir.glob("*.json"))
    ok(f"Local datasets: {len(datasets)} file(s)")
    for dataset in datasets:
        try:
            count = len(json.loads(dataset.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            count = 0
        log(f"    {dataset}: {count} items")


def _print_runs(runs_dir: Path):
    if not runs_dir.exists():
        warn("No local runs. Run 'eagle-eval run --languages tier1'.")
        return

    runs = sorted(runs_dir.glob("*.json"))
    ok(f"Local runs: {len(runs)} JSON report(s)")
    if runs:
        log(f"    Latest: {runs[-1]}")
