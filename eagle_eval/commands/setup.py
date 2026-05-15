"""Initial project setup command."""

import yaml
import click

from eagle_eval.cli_output import heading, log, ok, warn
from eagle_eval.cli_runtime import config_path, data_dir, project_dir


@click.command("init")
@click.option("--dry-run", is_flag=True, help="Preview generated config without writing files")
@click.option("--verbose", is_flag=True, help="Show setup paths")
def init_command(dry_run, verbose):
    """Interactive setup — creates eval_config.yaml and config files."""
    heading("Eagle Eval Setup")
    path = config_path()
    root = project_dir()

    if verbose:
        log(f"  Project dir: {root}")
        log(f"  Config path: {path}")
    if path.exists() and not dry_run:
        if not click.confirm("  eval_config.yaml already exists. Overwrite?", default=False):
            log("  Keeping existing config.")
            return

    config = _prompt_config()
    rendered_config = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    if dry_run:
        warn("Dry run — no files were written")
        log("\n  Config preview:")
        log(rendered_config)
        return

    path.write_text(rendered_config, encoding="utf-8")
    ok(f"Created {path}")

    from eagle_eval.config import generate_config_files

    generate_config_files(config, root / "config")
    ok("Created config/languages.json and config/topics.json")
    data_dir().mkdir(parents=True, exist_ok=True)

    heading("Setup Complete")
    log("  Next steps:")
    log("    1. Set the API keys shown by: eagle-eval doctor")
    log(f"    2. Confirm the writer model: {config['test_cases']['writer_model']}")
    log("    3. Run: eagle-eval generate --languages tier1")


def _prompt_config() -> dict:
    app_name = click.prompt("  App name", default="MyApp")
    domain = click.prompt("  Domain (agriculture, healthcare, education, finance, legal, other)", default="agriculture")
    user_persona = click.prompt("  User persona (who is your end user?)", default="smallholder farmer using a basic phone")
    agent_module = click.prompt("  Agent Python module path", default="app.agent")
    agent_function = click.prompt("  Agent function name", default="run_conversation")
    topics = _csv_prompt("  Domain topics (comma-separated)", "crop disease, planting schedule, fertilizer, pest control, weather advice")
    tier1 = _csv_prompt("  Tier 1 languages (comma-separated ISO codes)", "en,hi,sw,fr,pt")
    tier2_raw = click.prompt("  Tier 2 languages (comma-separated, or 'none')", default="am,ha,yo,zu,ig,ar,bn,ta,te,mr")
    tier2 = [item.strip() for item in tier2_raw.split(",")] if tier2_raw.strip().lower() != "none" else []
    total_langs = click.prompt("  Total language count (tier 3 auto-filled)", default=50, type=int)
    prompt_versions = {name: click.prompt(f"    Current version for '{name}'", default=1, type=int) for name in _csv_prompt("  Managed prompt names (comma-separated)", "router,grounding,response-gen")}
    writer = click.prompt("  Test-case writer service", default="gemini")
    writer_model = click.prompt("  Test-case writer model", default="gemini-2.0-flash")
    scorer = click.prompt("  Scoring service", default="gemini")
    scorer_model = click.prompt("  Scoring model", default="gemini-3.1-pro")
    destination = click.prompt("  Result destination", default="local")
    convs = click.prompt("  Conversations per language", default=10, type=int)
    turns = click.prompt("  Turns per conversation", default=10, type=int)

    return {
        "app_name": app_name,
        "domain": domain,
        "user_persona": user_persona,
        "app_context": _app_context(domain, user_persona),
        "agent": {"module": agent_module, "function": agent_function},
        "domain_topics": topics,
        "languages": {"count": total_langs, "tier1": tier1, "tier2": tier2},
        "prompt_versions": {"current": prompt_versions},
        "test_cases": {"writer": writer, "writer_model": writer_model, "conversations_per_language": convs, "turns_per_conversation": turns, "max_concurrency": 5, "quality_threshold": 3.5},
        "scoring": {"scorer": scorer, "scorer_model": scorer_model, "max_concurrency": 5, "item_timeout_seconds": 120, "regression_threshold": 0.05},
        "results": {"destination": destination, "local": {"directory": "data/results", "include_model_scorers": False}},
        "langfuse": {"dataset_prefix": "evals"},
    }


def _csv_prompt(label: str, default: str) -> list[str]:
    return [item.strip() for item in click.prompt(label, default=default).split(",") if item.strip()]


def _app_context(domain: str, user_persona: str) -> dict:
    agriculture = domain.strip().lower() == "agriculture"
    north_star_name = "monthly_unique_farmer_queries_resolved" if agriculture else "monthly_unique_user_queries_resolved"
    north_star_definition = (
        "A farmer query is resolved when the assistant either gives a safe, actionable answer or correctly asks for the minimum clarification needed and then resolves the query after clarification."
        if agriculture
        else "A user query is resolved when the assistant gives a safe, correct, actionable answer or asks the minimum clarification needed to resolve it."
    )
    return {
        "product": f"{domain.title()} advisory assistant",
        "user": user_persona,
        "north_star": {"name": north_star_name, "definition": north_star_definition},
        "resolution_policy": {
            "answerable_now": {"expectation": "Answer directly with actionable, safe, local advice."},
            "unclear_intent": {"expectation": "Ask a focused clarification question instead of guessing."},
            "missing_critical_context": {"expectation": "Ask for the minimum missing facts needed to answer safely."},
            "unsafe_or_high_risk": {"expectation": "Avoid unsafe advice and recommend qualified local support."},
        },
    }
