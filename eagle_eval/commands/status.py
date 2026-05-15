"""Status command."""

import json

import click

from eagle_eval.cli_output import err, heading, log, ok, print_local_status, warn
from eagle_eval.cli_runtime import config_path, data_dir, load_optional_config, project_dir


@click.command()
@click.option("--dry-run", is_flag=True, help="Only inspect local state; do not connect to the result destination")
@click.option("--verbose", is_flag=True, help="Show resolved paths")
def status(dry_run, verbose):
    """Show current datasets, items counts, and last run scores."""
    heading("Eval Status")
    config = load_optional_config()
    prefix = config.get("langfuse", {}).get("dataset_prefix", "evals")
    destination = str(config.get("results", {}).get("destination", "langfuse")).strip().lower()

    if verbose:
        log(f"  Project dir: {project_dir()}")
        log(f"  Config path: {config_path()}")
        log(f"  Data dir: {data_dir()}")

    if dry_run:
        warn("Dry run — skipped result-destination connection")
    elif destination == "local":
        print_local_status(project_dir(), config)
    elif destination != "langfuse":
        warn(f"Live status currently supports Langfuse. Configured result destination: {destination}")
        log("  Run 'eagle-eval doctor --verbose' to inspect SDK readiness.")
    else:
        _print_langfuse_status(prefix)

    _print_local_data_state()


def _print_langfuse_status(prefix: str):
    try:
        from langfuse import get_client

        client = get_client()
    except Exception as exc:
        err(f"Cannot connect to Langfuse result destination: {exc}")
        log("  Check LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST")
        return

    try:
        datasets = client.api.datasets.list()
        eval_datasets = [dataset for dataset in datasets.data if dataset.name.startswith(f"{prefix}/")]
        if not eval_datasets:
            warn("No eval datasets found. Run 'generate' and 'upload' first.")
            return
        log(f"\n  Datasets ({len(eval_datasets)}):")
        for dataset in eval_datasets:
            items = client.api.dataset_items.list(dataset_name=dataset.name)
            log(f"    {dataset.name}: {len(items.data)} items")
    except Exception as exc:
        err(f"Error fetching datasets: {exc}")


def _print_local_data_state():
    log("\n  Local data:")
    manifest_path = data_dir() / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ok(f"manifest.json: {len(manifest.get('conversations', []))} conversations")
    else:
        warn("No local data. Run 'generate' first.")

    report_path = data_dir() / "quality_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        ok(f"quality_report.json: {report.get('passed', '?')}/{report.get('total', '?')} passed")
    else:
        warn("No quality report. Run 'gate' first.")
