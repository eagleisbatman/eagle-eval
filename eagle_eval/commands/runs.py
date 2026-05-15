"""Experiment run and comparison commands."""

import copy
import json
import sys
from pathlib import Path

import click

from eagle_eval.cli_output import err, heading, log, ok, print_comparison_table, print_local_result_paths, print_results_table, warn
from eagle_eval.cli_runtime import load_config, parse_json_object, project_dir, resolve_languages


@click.command("run")
@click.option("--languages", default="tier1", help="Comma-separated ISO codes, or 'tier1', 'tier2', 'all'")
@click.option("--prompt-versions", default=None, help='JSON string like \'{"router":14,"grounding":3}\'. Defaults to current from config.')
@click.option("--agent-module", default=None, help="Override agent.module for this run without editing eval_config.yaml")
@click.option("--agent-function", default=None, help="Override agent.function for this run without editing eval_config.yaml")
@click.option("--run-prefix", default="", help="Prefix local/hosted run names, useful when replaying one dataset across agents")
@click.option("--max-concurrency", default=None, type=int, help="Override config concurrency")
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
def run(languages, prompt_versions, agent_module, agent_function, run_prefix, max_concurrency, dry_run, verbose):
    """Run agent against eval datasets and score with evaluators."""
    config = copy.deepcopy(load_config())
    lang_codes = resolve_languages(config, languages)
    _apply_agent_overrides(config, agent_module, agent_function)
    prompt_versions_value = parse_json_object(prompt_versions, "--prompt-versions") if prompt_versions else config["prompt_versions"]["current"]
    concurrency = max_concurrency if max_concurrency is not None else config["scoring"]["max_concurrency"]
    if concurrency < 1:
        raise click.BadParameter("must be at least 1", param_hint="--max-concurrency")

    heading("Run Experiment")
    log(f"  Languages: {', '.join(lang_codes)}")
    log(f"  Prompt versions: {json.dumps(prompt_versions_value)}")
    log(f"  Concurrency: {concurrency}")
    log(f"  Agent: {config['agent']['module']}.{config['agent']['function']}")
    if run_prefix:
        log(f"  Run prefix: {run_prefix}")
    if dry_run:
        warn("Dry run — agent will not be called")
        return

    from eagle_eval.experiment import run_experiment

    results = run_experiment(
        config, lang_codes, prompt_versions_value, concurrency,
        run_prefix=run_prefix, verbose=verbose, project_dir=project_dir()
    )
    heading("Results")
    print_results_table(results)
    print_local_result_paths(results)


@click.command()
@click.option("--baseline", required=True, help="JSON string for baseline prompt versions")
@click.option("--candidate", required=True, help="JSON string for candidate prompt versions")
@click.option("--languages", default="tier1")
@click.option("--output", default=None, help="Write results JSON to this path")
@click.option("--dry-run", is_flag=True, help="Show comparison plan without running experiments")
@click.option("--verbose", is_flag=True)
def compare(baseline, candidate, languages, output, dry_run, verbose):
    """Compare two prompt version configs on the same datasets."""
    config = load_config()
    lang_codes = resolve_languages(config, languages)
    baseline_pv = parse_json_object(baseline, "--baseline")
    candidate_pv = parse_json_object(candidate, "--candidate")
    threshold = config["scoring"]["regression_threshold"]

    heading("Prompt Version Comparison")
    log(f"  Baseline:  {json.dumps(baseline_pv)}")
    log(f"  Candidate: {json.dumps(candidate_pv)}")
    log(f"  Languages: {', '.join(lang_codes)}")
    log("  This runs the experiment TWICE (baseline + candidate).\n")
    if dry_run:
        warn("Dry run — experiments will not be executed")
        return
    if not click.confirm("  Continue?", default=True):
        return

    from eagle_eval.experiment import run_experiment

    concurrency = config["scoring"]["max_concurrency"]
    log("\n  Running baseline...", bold=True)
    baseline_results = run_experiment(config, lang_codes, baseline_pv, concurrency, run_prefix="baseline", verbose=verbose, project_dir=project_dir())
    log("\n  Running candidate...", bold=True)
    candidate_results = run_experiment(config, lang_codes, candidate_pv, concurrency, run_prefix="candidate", verbose=verbose, project_dir=project_dir())

    heading("Comparison")
    regressions = print_comparison_table(baseline_results, candidate_results, threshold)
    _write_comparison(output, baseline_results, candidate_results, regressions)
    if regressions:
        err(f"\n  {len(regressions)} regression(s) detected (>{threshold * 100}% drop)")
        sys.exit(1)
    ok("\n  No regressions detected")


def _apply_agent_overrides(config: dict, module: str | None, function: str | None):
    if module:
        config["agent"]["module"] = module
    if function:
        config["agent"]["function"] = function


def _write_comparison(output: str | None, baseline_results: dict, candidate_results: dict, regressions: list[dict]):
    if not output:
        return
    output_path = Path(output)
    output_path.write_text(json.dumps({"baseline": baseline_results, "candidate": candidate_results, "regressions": regressions}, indent=2), encoding="utf-8")
    log(f"\n  Results written to {output_path}")
