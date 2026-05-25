"""Cross-target comparison command."""

import json
from pathlib import Path

import click

from eagle_eval.cli_output import heading, log, ok, warn
from eagle_eval.cli_runtime import load_config, parse_json_object, project_dir, resolve_languages
from eagle_eval.file_io import atomic_write_json
from eagle_eval.target_compare import build_target_comparison
from eagle_eval.targets import apply_target, target_names


@click.command("compare-targets")
@click.option("--orchestrator", required=True, help="Named eval target for the full orchestrated flow")
@click.option("--sub-targets", required=True, help="Comma-separated sub-flow target names")
@click.option("--languages", default="tier1")
@click.option("--prompt-versions", default=None, help='JSON string like \'{"router":14}\'. Defaults to current config.')
@click.option("--max-concurrency", default=None, type=int)
@click.option("--output", default=None, help="Write comparison JSON to this path")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.option("--dry-run", is_flag=True, help="Show target comparison plan without running agents")
@click.option("--verbose", is_flag=True)
def compare_targets(orchestrator, sub_targets, languages, prompt_versions, max_concurrency, output, yes, dry_run, verbose):
    """Compare an orchestrated target against its sub-flow targets."""
    config = load_config()
    sub_target_names = [item.strip() for item in sub_targets.split(",") if item.strip()]
    if not sub_target_names:
        raise click.ClickException("--sub-targets must include at least one named eval target")
    targets = [orchestrator, *sub_target_names]
    _validate_targets(config, targets)
    lang_codes = resolve_languages(config, languages)
    prompt_versions_value = parse_json_object(prompt_versions, "--prompt-versions") if prompt_versions else config["prompt_versions"]["current"]
    concurrency = max_concurrency if max_concurrency is not None else config["scoring"]["max_concurrency"]
    if concurrency < 1:
        raise click.BadParameter("must be at least 1", param_hint="--max-concurrency")

    heading("Compare Eval Targets")
    log(f"  Orchestrator: {orchestrator}")
    log(f"  Sub-targets: {', '.join(sub_target_names)}")
    log(f"  Languages: {', '.join(lang_codes)}")
    log(f"  Prompt versions: {json.dumps(prompt_versions_value)}")
    if dry_run:
        warn("Dry run — target agents will not be called")
        return
    if not yes and not click.confirm("  Run each target on the same eval set?", default=True):
        return

    results = _run_targets(config, targets, lang_codes, prompt_versions_value, concurrency, verbose)
    comparison = build_target_comparison(results, orchestrator, sub_target_names)
    _print_comparison(comparison)
    _write_output(output, comparison, results)


def _validate_targets(config: dict, targets: list[str]):
    available = set(target_names(config))
    missing = [target for target in targets if target not in available]
    if missing:
        raise click.ClickException(f"Unknown eval target(s): {', '.join(missing)}. Available: {', '.join(sorted(available)) or 'none'}")


def _run_targets(config: dict, targets: list[str], lang_codes: list[str], prompt_versions: dict, concurrency: int, verbose: bool) -> dict:
    from eagle_eval.experiment import run_experiment

    results = {}
    for target in targets:
        target_config, _ = apply_target(config, target)
        log(f"\n  Running target: {target}", bold=True)
        results[target] = run_experiment(
            target_config, lang_codes, prompt_versions, concurrency,
            run_prefix=target, verbose=verbose, project_dir=project_dir(),
        )
    return results


def _print_comparison(comparison: dict):
    heading("Target Comparison")
    for target, stats in comparison["targets"].items():
        goal = _rate(stats.get("goal_achievement_rate"))
        action = _rate(stats.get("next_action_match_rate"))
        log(f"  {target}: goal={goal}, next_action={action}, failed_cases={stats.get('failed_cases', 0)}")
    if not comparison["gaps"]:
        ok("Orchestrated flow is aligned with sub-flow results")
        return
    for gap in comparison["gaps"]:
        warn(f"{gap['target']}: orchestrator delta {gap['goal_achievement_delta']:+.3f}")
        log(f"    {gap['recommendation']}")


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _write_output(output: str | None, comparison: dict, results: dict):
    if not output:
        return
    atomic_write_json(Path(output), {"comparison": comparison, "results": results})
    log(f"\n  Results written to {output}")
