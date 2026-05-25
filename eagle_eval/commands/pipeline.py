"""Generate, gate, and upload commands."""

import click

from eagle_eval.cli_output import err, heading, log, ok, pct, warn
from eagle_eval.cli_runtime import data_dir, load_config, project_dir, resolve_languages
from eagle_eval.file_io import atomic_write_json


@click.command()
@click.option("--languages", default="tier1", help="Comma-separated ISO codes, or 'tier1', 'tier2', 'all'")
@click.option("--dry-run", is_flag=True, help="Show what would be generated without calling APIs")
@click.option("--verbose", is_flag=True, help="Show detailed generation logs")
def generate(languages, dry_run, verbose):
    """Generate multilingual test conversations."""
    config = load_config()
    lang_codes = resolve_languages(config, languages)
    test_cases = config["test_cases"]
    total_calls = len(lang_codes) * test_cases["conversations_per_language"]

    heading("Generate Test Cases")
    log(f"  Languages: {', '.join(lang_codes)} ({len(lang_codes)} total)")
    log(f"  Conversations: {test_cases['conversations_per_language']} per language × {len(lang_codes)} = {total_calls}")
    log(f"  Turns per conversation: {test_cases['turns_per_conversation']}")
    log(f"  Test-case writer: {test_cases['writer']} ({test_cases['writer_model']})")
    log(f"  Estimated API calls: {total_calls}")
    if dry_run:
        warn("Dry run — nothing will be generated")
        return
    if total_calls > 20 and not click.confirm(f"\n  This will make ~{total_calls} API calls. Continue?", default=True):
        return

    from eagle_eval.generate import run_generation

    log("\n  Writing goal-aware test cases...", bold=True)
    results = run_generation(config, lang_codes, project_dir(), verbose=verbose)
    heading("Generation Complete")
    ok(f"Generated: {results['generated']} conversations")
    if results["failed"] > 0:
        warn(f"Failed: {results['failed']} (see logs)")
    log(f"  Output: {data_dir()}/")
    _print_sample(results.get("sample"))


@click.command()
@click.option("--dry-run", is_flag=True, help="Show checks without running LLM quality review")
@click.option("--verbose", is_flag=True)
def gate(dry_run, verbose):
    """Quality-check generated conversations before upload."""
    config = load_config()
    from eagle_eval.gate import run_quality_gate

    heading("Quality Gate")
    log("  Reviewing generated cases before they become regression data...", bold=True)
    results = run_quality_gate(config, data_dir(), dry_run=dry_run, verbose=verbose)
    log(f"\n  Total:   {results['total']}")
    ok(f"Passed:  {results['passed']} ({pct(results['passed'], results['total'])})")
    if results["flagged"] > 0:
        warn(f"Flagged: {results['flagged']} ({pct(results['flagged'], results['total'])})")
    if results["failed"] > 0:
        err(f"Failed:  {results['failed']} ({pct(results['failed'], results['total'])})")
    _print_language_quality(results.get("per_language", {}))

    report_path = data_dir() / "quality_report.json"
    if dry_run:
        warn("\nDry run — quality report was not written")
    else:
        atomic_write_json(report_path, results)
        log(f"\n  Full report: {report_path}")


@click.command()
@click.option("--languages", default="all", help="Comma-separated ISO codes, or 'tier1', 'tier2', 'all'")
@click.option("--recreate", is_flag=True, help="Delete existing datasets and recreate (default: append)")
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
def upload(languages, recreate, dry_run, verbose):
    """Send quality-gated conversations to the configured result destination."""
    config = load_config()
    lang_codes = resolve_languages(config, languages)
    from eagle_eval.upload import run_upload

    heading("Send to Result Destination")
    log(f"  Languages: {', '.join(lang_codes)}")
    log(f"  Mode: {'recreate' if recreate else 'append'}")
    destination = str(config.get("results", {}).get("destination", "langfuse")).strip().lower()
    if destination == "langfuse" and not recreate:
        warn("Langfuse append mode may duplicate existing items. Use --recreate for a clean hosted dataset.")
    if dry_run:
        warn("Dry run — nothing will be uploaded")

    log("\n  Preparing datasets for eval runs...", bold=True)
    try:
        results = run_upload(config, lang_codes, data_dir(), recreate=recreate, dry_run=dry_run, verbose=verbose)
    except (RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    heading("Upload Complete")
    for dataset_name, count in results["datasets"].items():
        ok(f"{dataset_name}: {count} items")
    log(f"  Total items: {results['total_items']}")


def _print_sample(sample: dict | None):
    if not sample:
        return
    log("\n  Sample conversation:")
    log(f"  [{sample['language']}] {sample['topic']}", fg="cyan")
    for index, turn in enumerate(sample["turns"][:3]):
        log(f"    Turn {index + 1}: {turn['content'][:80]}...")
    if len(sample["turns"]) > 3:
        log(f"    ... +{len(sample['turns']) - 3} more turns")


def _print_language_quality(per_language: dict):
    if not per_language:
        return
    log("\n  Per language:")
    for lang, stats in per_language.items():
        status = "✓" if stats["passed"] >= stats["total"] * 0.7 else "⚠"
        log(f"    {status} {lang}: {stats['passed']}/{stats['total']} passed (avg quality: {stats['avg_quality']:.1f})")
