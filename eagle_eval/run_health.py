"""Detect runs where every item errored so a failed run never reads as success.

`run_error` is emitted only when scoring an item raises (local_item_scoring), and
a successful item emits its real metric names instead. So a language whose only
score is `run_error` had 100% of its items fail — the run produced no real signal
and must exit non-zero, not print a green table.
"""

from __future__ import annotations

from eagle_eval.cli_output import err, warn


def run_error_summary(results: dict) -> dict:
    """Split languages into fully-failed (only run_error) and partially-failed."""
    scores = results.get("scores", {})
    fully_failed = [
        lang for lang, metrics in scores.items()
        if metrics and set(metrics) == {"run_error"}
    ]
    partial = [
        lang for lang, metrics in scores.items()
        if "run_error" in metrics and set(metrics) != {"run_error"}
    ]
    return {"total": len(scores), "fully_failed": fully_failed, "partial": partial}


def report_run_errors(results: dict) -> bool:
    """Warn on partial errors; loudly flag a total failure. True == total failure."""
    summary = run_error_summary(results)
    if summary["partial"]:
        warn(
            "Partial run errors in: "
            f"{', '.join(summary['partial'])} — some items hit run_error "
            "(see the JSON report's run_error comment)."
        )
    total = summary["total"]
    failed = summary["fully_failed"]
    if not total or len(failed) != total:
        return False
    err("RUN FAILED: every item errored (run_error) — no real scores were produced.")
    err(f"  Failed languages: {', '.join(failed)}")
    err(
        "  Inspect the JSON report's run_error comment. A common cause is an agent "
        "import failure (e.g. workspace packages missing from PYTHONPATH)."
    )
    return True
