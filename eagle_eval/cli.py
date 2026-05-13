"""CLI entry point. All commands support --dry-run and --verbose."""

import click
import json
import sys
import os
import shlex
import subprocess
from pathlib import Path

from eagle_eval import __version__


def _log(msg, bold=False, fg=None):
    click.echo(click.style(msg, bold=bold, fg=fg))


def _ok(msg):
    _log(f"  ✓ {msg}", fg="green")


def _warn(msg):
    _log(f"  ⚠ {msg}", fg="yellow")


def _err(msg):
    _log(f"  ✗ {msg}", fg="red")


def _heading(msg):
    _log(f"\n{'─'*50}", fg="cyan")
    _log(f"  {msg}", bold=True, fg="cyan")
    _log(f"{'─'*50}", fg="cyan")


def _project_dir():
    ctx = click.get_current_context(silent=True)
    if ctx and ctx.obj and ctx.obj.get("project_dir"):
        return ctx.obj["project_dir"]

    env_dir = os.environ.get("EAGLE_EVAL_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.cwd().resolve()


def _config_path():
    return _project_dir() / "eval_config.yaml"


def _data_dir():
    return _project_dir() / "data" / "synthetic"


def _load_config():
    from eagle_eval.config import load_config
    try:
        return load_config(_config_path())
    except (FileNotFoundError, ValueError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc


def _load_optional_config():
    from eagle_eval.config import load_config
    try:
        return load_config(_config_path())
    except (FileNotFoundError, ValueError, TypeError):
        return {}


@click.group()
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Directory containing eval_config.yaml and data/. Defaults to the current directory.",
)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, project_dir):
    """Eagle Eval pipeline for multilingual LLM apps.

    Run 'init' first to create eval_config.yaml, then generate → gate → upload → run.
    """
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = (project_dir or Path.cwd()).expanduser().resolve()


# ─── init ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview generated config without writing files")
@click.option("--verbose", is_flag=True, help="Show setup paths")
def init(dry_run, verbose):
    """Interactive setup — creates eval_config.yaml and config files."""
    _heading("Eagle Eval Setup")

    config_path = _config_path()
    project_dir = _project_dir()
    data_dir = _data_dir()

    if verbose:
        _log(f"  Project dir: {project_dir}")
        _log(f"  Config path: {config_path}")

    if config_path.exists() and not dry_run:
        if not click.confirm(f"  eval_config.yaml already exists. Overwrite?", default=False):
            _log("  Keeping existing config.")
            return

    app_name = click.prompt("  App name", default="MyApp")
    domain = click.prompt("  Domain (agriculture, healthcare, education, finance, legal, other)", default="agriculture")
    user_persona = click.prompt("  User persona (who is your end user?)", default="smallholder farmer using a basic phone")

    agent_module = click.prompt("  Agent Python module path", default="app.agent")
    agent_function = click.prompt("  Agent function name", default="run_conversation")

    topics_raw = click.prompt("  Domain topics (comma-separated)", default="crop disease, planting schedule, fertilizer, pest control, weather advice")
    topics = [t.strip() for t in topics_raw.split(",")]

    tier1_raw = click.prompt("  Tier 1 languages (comma-separated ISO codes)", default="en,hi,sw,fr,pt")
    tier1 = [l.strip() for l in tier1_raw.split(",")]

    tier2_raw = click.prompt("  Tier 2 languages (comma-separated, or 'none')", default="am,ha,yo,zu,ig,ar,bn,ta,te,mr")
    tier2 = [l.strip() for l in tier2_raw.split(",")] if tier2_raw.strip().lower() != "none" else []

    total_langs = click.prompt("  Total language count (tier 3 auto-filled)", default=50, type=int)

    prompt_names_raw = click.prompt("  Managed prompt names (comma-separated)", default="router,grounding,response-gen")
    prompt_names = [p.strip() for p in prompt_names_raw.split(",")]

    prompt_versions = {}
    for p in prompt_names:
        v = click.prompt(f"    Current version for '{p}'", default=1, type=int)
        prompt_versions[p] = v

    writer = click.prompt("  Test-case writer service", default="gemini")
    writer_model = click.prompt("  Test-case writer model", default="gemini-2.0-flash")
    scorer = click.prompt("  Scoring service", default="gemini")
    scorer_model = click.prompt("  Scoring model", default="gemini-3.1-pro")
    result_destination = click.prompt("  Result destination", default="langfuse")

    convs_per_lang = click.prompt("  Conversations per language", default=10, type=int)
    turns_per_conv = click.prompt("  Turns per conversation", default=10, type=int)
    north_star_name = (
        "monthly_unique_farmer_queries_resolved"
        if domain.strip().lower() == "agriculture"
        else "monthly_unique_user_queries_resolved"
    )
    north_star_definition = (
        "A farmer query is resolved when the assistant either gives a safe, actionable answer "
        "or correctly asks for the minimum clarification needed and then resolves the query after clarification."
        if domain.strip().lower() == "agriculture"
        else "A user query is resolved when the assistant gives a safe, correct, actionable answer or asks the minimum clarification needed to resolve it."
    )

    config = {
        "app_name": app_name,
        "domain": domain,
        "user_persona": user_persona,
        "app_context": {
            "product": f"{domain.title()} advisory assistant",
            "user": user_persona,
            "north_star": {
                "name": north_star_name,
                "definition": north_star_definition,
            },
            "resolution_policy": {
                "answerable_now": {
                    "expectation": "Answer directly with actionable, safe, local advice.",
                },
                "unclear_intent": {
                    "expectation": "Ask a focused clarification question instead of guessing.",
                },
                "missing_critical_context": {
                    "expectation": "Ask for the minimum missing facts needed to answer safely.",
                },
                "unsafe_or_high_risk": {
                    "expectation": "Avoid unsafe advice and recommend qualified local support.",
                },
            },
        },
        "agent": {
            "module": agent_module,
            "function": agent_function,
        },
        "domain_topics": topics,
        "languages": {
            "count": total_langs,
            "tier1": tier1,
            "tier2": tier2,
        },
        "prompt_versions": {
            "current": prompt_versions,
        },
        "test_cases": {
            "writer": writer,
            "writer_model": writer_model,
            "conversations_per_language": convs_per_lang,
            "turns_per_conversation": turns_per_conv,
            "max_concurrency": 5,
            "quality_threshold": 3.5,
        },
        "scoring": {
            "scorer": scorer,
            "scorer_model": scorer_model,
            "max_concurrency": 5,
            "item_timeout_seconds": 120,
            "regression_threshold": 0.05,
        },
        "results": {
            "destination": result_destination,
        },
        "langfuse": {
            "dataset_prefix": "evals",
        },
    }

    import yaml
    rendered_config = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)

    if dry_run:
        _warn("Dry run — no files were written")
        _log("\n  Config preview:")
        _log(rendered_config)
        return

    config_path.write_text(rendered_config)
    _ok(f"Created {config_path}")

    # Generate languages.json and topics.json
    from eagle_eval.config import generate_config_files
    generate_config_files(config, project_dir / "config")
    _ok("Created config/languages.json and config/topics.json")

    data_dir.mkdir(parents=True, exist_ok=True)

    _heading("Setup Complete")
    _log("  Next steps:")
    _log("    1. Set the API keys shown by: eagle-eval doctor")
    _log(f"    2. Confirm the writer model: {writer_model}")
    _log("    3. Run: eagle-eval generate --languages tier1")


# ─── generate ───────────────────────────────────────────────────────────────

@cli.command()
@click.option("--languages", default="tier1", help="Comma-separated ISO codes, or 'tier1', 'tier2', 'all'")
@click.option("--dry-run", is_flag=True, help="Show what would be generated without calling APIs")
@click.option("--verbose", is_flag=True, help="Show detailed generation logs")
def generate(languages, dry_run, verbose):
    """Generate multilingual test conversations."""
    config = _load_config()
    from eagle_eval.generate import run_generation

    lang_codes = _resolve_languages(config, languages)
    project_dir = _project_dir()
    data_dir = _data_dir()

    convs = config["test_cases"]["conversations_per_language"]
    turns = config["test_cases"]["turns_per_conversation"]
    total_calls = len(lang_codes) * convs
    model = config["test_cases"]["writer_model"]

    _heading("Generate Test Cases")
    _log(f"  Languages: {', '.join(lang_codes)} ({len(lang_codes)} total)")
    _log(f"  Conversations: {convs} per language × {len(lang_codes)} = {total_calls}")
    _log(f"  Turns per conversation: {turns}")
    _log(f"  Test-case writer: {config['test_cases']['writer']} ({model})")
    _log(f"  Estimated API calls: {total_calls}")

    if dry_run:
        _warn("Dry run — nothing will be generated")
        return

    if total_calls > 20:
        if not click.confirm(f"\n  This will make ~{total_calls} API calls. Continue?", default=True):
            return

    results = run_generation(config, lang_codes, project_dir, verbose=verbose)

    _heading("Generation Complete")
    _ok(f"Generated: {results['generated']} conversations")
    if results["failed"] > 0:
        _warn(f"Failed: {results['failed']} (see logs)")
    _log(f"  Output: {data_dir}/")

    # Show a sample
    if results["generated"] > 0 and results.get("sample"):
        _log("\n  Sample conversation:")
        sample = results["sample"]
        _log(f"  [{sample['language']}] {sample['topic']}", fg="cyan")
        for i, turn in enumerate(sample["turns"][:3]):
            _log(f"    Turn {i+1}: {turn['content'][:80]}...")
        if len(sample["turns"]) > 3:
            _log(f"    ... +{len(sample['turns'])-3} more turns")


# ─── gate ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--dry-run", is_flag=True, help="Show checks without running LLM quality review")
@click.option("--verbose", is_flag=True)
def gate(dry_run, verbose):
    """Quality-check generated conversations before upload."""
    config = _load_config()
    from eagle_eval.gate import run_quality_gate
    data_dir = _data_dir()

    _heading("Quality Gate")

    results = run_quality_gate(config, data_dir, dry_run=dry_run, verbose=verbose)

    _log(f"\n  Total:   {results['total']}")
    _ok(f"Passed:  {results['passed']} ({_pct(results['passed'], results['total'])})")
    if results["flagged"] > 0:
        _warn(f"Flagged: {results['flagged']} ({_pct(results['flagged'], results['total'])})")
    if results["failed"] > 0:
        _err(f"Failed:  {results['failed']} ({_pct(results['failed'], results['total'])})")

    if results.get("per_language"):
        _log("\n  Per language:")
        for lang, stats in results["per_language"].items():
            status = "✓" if stats["passed"] >= stats["total"] * 0.7 else "⚠"
            _log(f"    {status} {lang}: {stats['passed']}/{stats['total']} passed (avg quality: {stats['avg_quality']:.1f})")

    report_path = data_dir / "quality_report.json"
    if dry_run:
        _warn("\nDry run — quality report was not written")
    else:
        report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        _log(f"\n  Full report: {report_path}")


# ─── upload ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--languages", default="all", help="Comma-separated ISO codes, or 'tier1', 'tier2', 'all'")
@click.option("--recreate", is_flag=True, help="Delete existing datasets and recreate (default: append)")
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
def upload(languages, recreate, dry_run, verbose):
    """Send quality-gated conversations to the configured result destination."""
    config = _load_config()
    from eagle_eval.upload import run_upload

    lang_codes = _resolve_languages(config, languages)
    data_dir = _data_dir()

    _heading("Send to Result Destination")
    _log(f"  Languages: {', '.join(lang_codes)}")
    _log(f"  Mode: {'recreate' if recreate else 'append'}")

    if dry_run:
        _warn("Dry run — nothing will be uploaded")

    results = run_upload(config, lang_codes, data_dir, recreate=recreate, dry_run=dry_run, verbose=verbose)

    _heading("Upload Complete")
    for ds_name, count in results["datasets"].items():
        _ok(f"{ds_name}: {count} items")
    _log(f"  Total items: {results['total_items']}")


# ─── run ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--languages", default="tier1", help="Comma-separated ISO codes, or 'tier1', 'tier2', 'all'")
@click.option("--prompt-versions", default=None, help='JSON string like \'{"router":14,"grounding":3}\'. Defaults to current from config.')
@click.option("--max-concurrency", default=None, type=int, help="Override config concurrency")
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
def run(languages, prompt_versions, max_concurrency, dry_run, verbose):
    """Run agent against eval datasets and score with evaluators."""
    config = _load_config()
    from eagle_eval.experiment import run_experiment

    lang_codes = _resolve_languages(config, languages)

    pv = (
        _parse_json_object(prompt_versions, "--prompt-versions")
        if prompt_versions
        else config["prompt_versions"]["current"]
    )
    concurrency = max_concurrency if max_concurrency is not None else config["scoring"]["max_concurrency"]
    if concurrency < 1:
        raise click.BadParameter("must be at least 1", param_hint="--max-concurrency")

    _heading("Run Experiment")
    _log(f"  Languages: {', '.join(lang_codes)}")
    _log(f"  Prompt versions: {json.dumps(pv)}")
    _log(f"  Concurrency: {concurrency}")
    _log(f"  Agent: {config['agent']['module']}.{config['agent']['function']}")

    if dry_run:
        _warn("Dry run — agent will not be called")
        return

    results = run_experiment(config, lang_codes, pv, concurrency, verbose=verbose, project_dir=_project_dir())

    _heading("Results")
    _print_results_table(results)


# ─── compare ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--baseline", required=True, help='JSON string for baseline prompt versions')
@click.option("--candidate", required=True, help='JSON string for candidate prompt versions')
@click.option("--languages", default="tier1")
@click.option("--output", default=None, help="Write results JSON to this path")
@click.option("--dry-run", is_flag=True, help="Show comparison plan without running experiments")
@click.option("--verbose", is_flag=True)
def compare(baseline, candidate, languages, output, dry_run, verbose):
    """Compare two prompt version configs on the same datasets."""
    config = _load_config()

    lang_codes = _resolve_languages(config, languages)
    baseline_pv = _parse_json_object(baseline, "--baseline")
    candidate_pv = _parse_json_object(candidate, "--candidate")
    concurrency = config["scoring"]["max_concurrency"]
    threshold = config["scoring"]["regression_threshold"]

    _heading("Prompt Version Comparison")
    _log(f"  Baseline:  {json.dumps(baseline_pv)}")
    _log(f"  Candidate: {json.dumps(candidate_pv)}")
    _log(f"  Languages: {', '.join(lang_codes)}")
    _log(f"  This runs the experiment TWICE (baseline + candidate).\n")

    if dry_run:
        _warn("Dry run — experiments will not be executed")
        return

    if not click.confirm("  Continue?", default=True):
        return

    from eagle_eval.experiment import run_experiment

    _log("\n  Running baseline...", bold=True)
    baseline_results = run_experiment(
        config, lang_codes, baseline_pv, concurrency, run_prefix="baseline", verbose=verbose, project_dir=_project_dir()
    )

    _log("\n  Running candidate...", bold=True)
    candidate_results = run_experiment(
        config, lang_codes, candidate_pv, concurrency, run_prefix="candidate", verbose=verbose, project_dir=_project_dir()
    )

    _heading("Comparison")
    regressions = _print_comparison_table(baseline_results, candidate_results, threshold)

    if output:
        out_path = Path(output)
        out_path.write_text(json.dumps({
            "baseline": baseline_results,
            "candidate": candidate_results,
            "regressions": regressions,
        }, indent=2))
        _log(f"\n  Results written to {out_path}")

    if regressions:
        _err(f"\n  {len(regressions)} regression(s) detected (>{threshold*100}% drop)")
        sys.exit(1)
    else:
        _ok("\n  No regressions detected")


# ─── status ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--dry-run", is_flag=True, help="Only inspect local state; do not connect to the result destination")
@click.option("--verbose", is_flag=True, help="Show resolved paths")
def status(dry_run, verbose):
    """Show current datasets, items counts, and last run scores."""
    _heading("Eval Status")

    config = _load_optional_config()
    data_dir = _data_dir()
    prefix = config.get("langfuse", {}).get("dataset_prefix", "evals")
    destination = str(config.get("results", {}).get("destination", "langfuse")).strip().lower()

    if verbose:
        _log(f"  Project dir: {_project_dir()}")
        _log(f"  Config path: {_config_path()}")
        _log(f"  Data dir: {data_dir}")

    if dry_run:
        _warn("Dry run — skipped result-destination connection")
    elif destination != "langfuse":
        _warn(f"Live status currently supports Langfuse. Configured result destination: {destination}")
        _log("  Run 'eagle-eval doctor --verbose' to inspect SDK readiness.")
    else:
        try:
            from langfuse import get_client
            lf = get_client()
        except Exception as e:
            _err(f"Cannot connect to Langfuse result destination: {e}")
            _log("  Check LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST")
            lf = None

        if lf:
            try:
                datasets = lf.api.datasets.list()
                eval_datasets = [d for d in datasets.data if d.name.startswith(f"{prefix}/")]

                if not eval_datasets:
                    _warn("No eval datasets found. Run 'generate' and 'upload' first.")
                else:
                    _log(f"\n  Datasets ({len(eval_datasets)}):")
                    for d in eval_datasets:
                        items = lf.api.dataset_items.list(dataset_name=d.name)
                        _log(f"    {d.name}: {len(items.data)} items")
            except Exception as e:
                _err(f"Error fetching datasets: {e}")

    # Check local data
    _log(f"\n  Local data:")
    manifest_path = data_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        _ok(f"manifest.json: {len(manifest.get('conversations', []))} conversations")
    else:
        _warn("No local data. Run 'generate' first.")

    report_path = data_dir / "quality_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        _ok(f"quality_report.json: {report.get('passed', '?')}/{report.get('total', '?')} passed")
    else:
        _warn("No quality report. Run 'gate' first.")


# ─── doctor ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--verbose", is_flag=True, help="Show docs links and every checked key")
def doctor(verbose):
    """Explain config roles and check local integration readiness."""
    _heading("Eagle Eval Doctor")

    config = _load_optional_config()
    if not config:
        _warn("No eval_config.yaml found. Run 'eagle-eval init' first.")
    else:
        test_cases = config.get("test_cases", {})
        scoring = config.get("scoring", {})
        results = config.get("results", {})
        app_context = config.get("app_context", {})
        north_star = app_context.get("north_star", {})
        _log("  Config roles:")
        _log(f"    App context:      {app_context.get('product', '?')}")
        _log(f"    North Star:       {north_star.get('name', '?')}")
        _log(f"    Test-case writer: {test_cases.get('writer', '?')} ({test_cases.get('writer_model', '?')})")
        _log(f"    Scorer:           {scoring.get('scorer', '?')} ({scoring.get('scorer_model', '?')})")
        _log(f"    Result destination: {results.get('destination', '?')}")

    from eagle_eval.integrations import check_integrations

    _log("\n  Integration readiness:")
    for item in check_integrations(config):
        marker = "*" if item["configured"] else " "
        package_ok = all(item["packages"].values())
        env_ok = all(item["env"].values())
        package_msg = "SDK installed" if package_ok else "SDK missing"
        env_msg = "env ready" if env_ok else "env missing"
        line = f"  {marker} {item['label']}: {package_msg}, {env_msg}"
        if item["configured"] and package_ok and env_ok:
            _ok(line.strip())
        elif item["configured"]:
            _warn(line.strip())
        else:
            _log(line)

        if verbose:
            packages = ", ".join(f"{name}={'ok' if ok else 'missing'}" for name, ok in item["packages"].items())
            env = ", ".join(f"{name}={'set' if ok else 'missing'}" for name, ok in item["env"].items())
            _log(f"      Purpose: {item['purpose']}")
            _log(f"      Packages: {packages}")
            _log(f"      Env: {env}")
            _log(f"      Docs: {item['docs_url']}")

    if config:
        from eagle_eval.custom_scoring import check_custom_metrics

        custom_statuses = check_custom_metrics(config, _project_dir())
        if custom_statuses:
            _log("\n  Custom metrics:")
            for status in custom_statuses:
                if status.ok:
                    _ok(f"{status.name}: {status.path}")
                else:
                    _warn(f"{status.name}: {status.path} ({status.error})")

    _log("\n  What a completed eval gives you:")
    _log("    - generated multilingual test cases under data/synthetic/")
    _log("    - quality_report.json showing which test cases are ready")
    _log("    - scored agent runs with per-language metrics")
    _log("    - a regression decision when comparing prompt/model versions")


# ─── context ────────────────────────────────────────────────────────────────

@cli.group("context")
def context_group():
    """View the product context used by scorers."""


@context_group.command("view")
@click.option("--json-output", is_flag=True, help="Print the raw app_context JSON")
def context_view(json_output):
    """Show the app use case, North Star, and resolution policy."""
    config = _load_config()
    app_context = config["app_context"]
    if json_output:
        _log(json.dumps(app_context, indent=2, ensure_ascii=False))
        return

    north_star = app_context.get("north_star", {})
    _heading("App Context")
    _log(f"  Product:    {app_context.get('product', config.get('app_name'))}")
    _log(f"  User:       {app_context.get('user', config.get('user_persona'))}")
    _log(f"  North Star: {north_star.get('name')}")
    _log(f"  Definition: {north_star.get('definition')}")

    policy = app_context.get("resolution_policy", {})
    if policy:
        _log("\n  Resolution policy:")
        for scenario, details in policy.items():
            expectation = details.get("expectation") if isinstance(details, dict) else str(details)
            _log(f"    - {scenario}: {expectation}")


# ─── scorer ─────────────────────────────────────────────────────────────────

@cli.group("scorer")
def scorer_group():
    """Create, list, and test custom scorers."""


@scorer_group.command("list")
def scorer_list():
    """List configured custom scorers and built-in templates."""
    config = _load_optional_config()
    from eagle_eval.custom_scoring import configured_custom_metrics, check_custom_metrics
    from eagle_eval.scorer_templates import SCORER_TEMPLATES

    _heading("Custom Scorers")
    metrics = configured_custom_metrics(config)
    if metrics:
        statuses = {status.name: status for status in check_custom_metrics(config, _project_dir())}
        for metric in metrics:
            name = metric["name"]
            enabled = metric.get("enabled", True)
            status = statuses.get(name)
            suffix = "disabled" if not enabled else ("ready" if status and status.ok else "not importable")
            _log(f"  - {name}: {metric['path']} ({suffix})")
    else:
        _warn("No custom metrics configured in scoring.custom_metrics.")

    _log("\n  Templates:")
    for name, template in SCORER_TEMPLATES.items():
        _log(f"    - {name}: {template['description']}")


@scorer_group.command("init")
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite an existing scorer file")
@click.option("--sample", is_flag=True, help="Also write a sample scorer input JSON")
def scorer_init(name, force, sample):
    """Create a developer-owned scorer template."""
    from eagle_eval.scorer_templates import SCORER_TEMPLATES, write_sample_case, write_scorer_template

    if name not in SCORER_TEMPLATES:
        valid = ", ".join(sorted(SCORER_TEMPLATES))
        raise click.ClickException(f"Unknown scorer template '{name}'. Available: {valid}")

    _heading("Create Custom Scorer")
    try:
        path = write_scorer_template(name, _project_dir(), force=force)
    except FileExistsError as exc:
        raise click.ClickException(f"{exc} already exists. Use --force to overwrite.") from exc

    _ok(f"Created {path.relative_to(_project_dir())}")
    _log("\n  Add this to eval_config.yaml under scoring.custom_metrics:")
    _log("    - name: " + name)
    _log("      path: " + SCORER_TEMPLATES[name]["path"])
    _log("      weight: 0.45")
    _log("      required: true")

    if sample:
        sample_path = write_sample_case(_project_dir() / "examples" / "scorer_sample.json")
        _ok(f"Created {sample_path.relative_to(_project_dir())}")


@scorer_group.command("test")
@click.argument("name")
@click.option("--sample", "sample_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="JSON file with input/output/expected_output/metadata")
def scorer_test(name, sample_path):
    """Run one custom scorer locally against a sample JSON payload."""
    config = _load_config()
    from eagle_eval.custom_scoring import configured_custom_metrics, load_custom_evaluator
    from eagle_eval.scorer_templates import SCORER_TEMPLATES, sample_case

    if sample_path:
        payload = json.loads(Path(sample_path).read_text(encoding="utf-8"))
    else:
        payload = sample_case(name)

    try:
        evaluator = load_custom_evaluator(config, _project_dir(), name)
    except KeyError:
        metric = next(
            (candidate for candidate in configured_custom_metrics(config) if candidate["name"] == name),
            None,
        )
        if metric is None and name in SCORER_TEMPLATES:
            metric = {"name": name, "path": SCORER_TEMPLATES[name]["path"]}
        if metric is None:
            raise
        test_config = {
            **config,
            "scoring": {
                **config["scoring"],
                "custom_metrics": [{**metric, "enabled": True}],
            },
        }
        evaluator = load_custom_evaluator(test_config, _project_dir(), name)
    result = evaluator(
        input=payload.get("input", {}),
        output=payload.get("output", {}),
        expected_output=payload.get("expected_output", {}),
        metadata=payload.get("metadata", {}),
    )

    _heading("Scorer Test")
    _log(f"  Name:    {result.name}")
    _log(f"  Score:   {result.value:.3f}")
    if result.comment:
        _log(f"  Comment: {result.comment}")


# ─── install-assistants ─────────────────────────────────────────────────────

@cli.command("install-assistants")
@click.option("--tool", type=click.Choice(["all", "codex", "claude"]), default="all", show_default=True)
@click.option("--yes", is_flag=True, help="Write files without asking for confirmation")
@click.option("--force", is_flag=True, help="Overwrite existing helper files")
def install_assistants(tool, yes, force):
    """Install Codex and Claude Code helper files for this eval workflow."""
    project_dir = _project_dir()
    _heading("Install Assistant Helpers")
    _log(f"  Project dir: {project_dir}")
    _log(f"  Target: {tool}")

    if not yes:
        if not click.confirm("  Write project helper files?", default=True):
            _log("  No files written.")
            return

    from eagle_eval.assistant_install import install_assistant_support

    actions = install_assistant_support(project_dir, tool=tool, force=force)
    for action in actions:
        rel = action.path.relative_to(project_dir)
        if action.status == "skipped":
            _warn(f"Skipped existing {rel} (use --force to overwrite)")
        elif action.status == "updated":
            _ok(f"Updated {rel}")
        else:
            _ok(f"Created {rel}")


# ─── update ──────────────────────────────────────────────────────────────────

@cli.command("update")
@click.option("--source", default=None, help="pip install target, e.g. package name or git+https URL")
@click.option("--pre", is_flag=True, help="Allow prerelease versions")
@click.option("--dry-run", is_flag=True, help="Print the update command without running it")
@click.option("--verbose", is_flag=True, help="Show update source resolution details")
def update(source, pre, dry_run, verbose):
    """Upgrade Eagle Eval via pip."""
    _self_update(source=source, pre=pre, dry_run=dry_run, verbose=verbose)


# ─── helpers ────────────────────────────────────────────────────────────────

def _resolve_languages(config, lang_arg):
    """Resolve 'tier1', 'tier2', 'all', or comma-separated codes."""
    langs = config["languages"]
    lang_arg = (lang_arg or "").strip().lower()
    if lang_arg == "tier1":
        resolved = langs.get("tier1", [])
    elif lang_arg == "tier2":
        resolved = langs.get("tier2", [])
    elif lang_arg == "all":
        resolved = _all_configured_languages(config)
    else:
        resolved = [l.strip().lower() for l in lang_arg.split(",") if l.strip()]

    resolved = _dedupe(resolved)
    if not resolved:
        raise click.ClickException(f"No languages resolved from '{lang_arg}'.")
    return resolved


def _all_configured_languages(config):
    generated_languages = _project_dir() / "config" / "languages.json"
    if generated_languages.exists():
        try:
            payload = json.loads(generated_languages.read_text())
            return [item["code"] for item in payload if item.get("code")]
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise click.ClickException(f"Invalid languages file: {generated_languages}: {exc}") from exc

    from eagle_eval.config import ALL_LANGUAGES

    language_config = config["languages"]
    target_count = int(language_config.get("count") or 0)
    configured = _dedupe(language_config.get("tier1", []) + language_config.get("tier2", []))
    target_count = max(target_count, len(configured))

    resolved = list(configured)
    for language in ALL_LANGUAGES:
        if len(resolved) >= target_count:
            break
        code = language["code"]
        if code not in resolved:
            resolved.append(code)
    return resolved


def _dedupe(values):
    seen = set()
    result = []
    for value in values:
        normalized = str(value).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _parse_json_object(value, option_name):
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"invalid JSON: {exc.msg}", param_hint=option_name) from exc

    if not isinstance(parsed, dict):
        raise click.BadParameter("must be a JSON object", param_hint=option_name)
    return parsed


def _self_update(source, pre, dry_run, verbose):
    config = _load_optional_config()
    source = (
        source
        or os.environ.get("EAGLE_EVAL_UPDATE_SOURCE")
        or config.get("updates", {}).get("source")
        or "eagle-eval"
    )

    command = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if pre:
        command.append("--pre")
    command.append(source)

    _heading("Eagle Eval Update")
    _log(f"  Current version: {__version__}")
    _log(f"  Update source: {source}")
    if verbose:
        _log(f"  Project dir: {_project_dir()}")
        _log(f"  Config path: {_config_path()}")
    _log("\n  Command:")
    _log(f"    {shlex.join(command)}")

    if dry_run:
        _warn("\nDry run — update command was not executed")
        return

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"Update failed with exit code {exc.returncode}") from exc


def _pct(n, total):
    return f"{n/total*100:.0f}%" if total else "0%"


def _print_results_table(results):
    """Print experiment results as a formatted table."""
    try:
        from tabulate import tabulate
    except ImportError:
        # Fallback to simple output
        for lang, scores in results.get("scores", {}).items():
            _log(f"  {lang}:")
            for metric, value in scores.items():
                _log(f"    {metric}: {value:.3f}")
        return

    rows = []
    for lang, scores in results.get("scores", {}).items():
        for metric, value in scores.items():
            rows.append([lang, metric, f"{value:.3f}"])

    _log(tabulate(rows, headers=["Language", "Metric", "Score"], tablefmt="rounded_grid"))


def _print_comparison_table(baseline_results, candidate_results, threshold):
    """Print side-by-side comparison. Returns list of regressions."""
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
            b = baseline_results["scores"][lang].get(metric, 0)
            c = candidate_results["scores"][lang].get(metric, 0)
            delta = c - b
            status = "✓" if delta >= -threshold else "⚠ REG"
            if delta < -threshold:
                regressions.append({"lang": lang, "metric": metric, "delta": delta})
            rows.append([lang, metric, f"{b:.3f}", f"{c:.3f}", f"{delta:+.3f}", status])

    if tabulate:
        _log(tabulate(rows, headers=["Language", "Metric", "Baseline", "Candidate", "Delta", "Status"], tablefmt="rounded_grid"))
    else:
        for row in rows:
            _log(f"  {row[0]:6s} {row[1]:25s} {row[2]:8s} {row[3]:8s} {row[4]:8s} {row[5]}")

    return regressions
