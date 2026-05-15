"""Doctor command."""

import click

from eagle_eval.cli_output import heading, log, ok, warn
from eagle_eval.cli_runtime import load_optional_config, project_dir


@click.command()
@click.option("--verbose", is_flag=True, help="Show docs links and every checked key")
def doctor(verbose):
    """Explain config roles and check local integration readiness."""
    heading("Eagle Eval Doctor")
    config = load_optional_config()
    if not config:
        warn("No eval_config.yaml found. Run 'eagle-eval init' first.")
    else:
        _print_config_roles(config)

    from eagle_eval.integrations import check_integrations

    log("\n  Integration readiness:")
    for item in check_integrations(config):
        _print_integration(item, verbose)

    if config:
        _print_custom_metrics(config)
    _print_completed_eval_summary(config)


def _print_config_roles(config: dict):
    test_cases = config.get("test_cases", {})
    scoring = config.get("scoring", {})
    results = config.get("results", {})
    app_context = config.get("app_context", {})
    north_star = app_context.get("north_star", {})
    log("  Config roles:")
    log(f"    App context:      {app_context.get('product', '?')}")
    log(f"    North Star:       {north_star.get('name', '?')}")
    log(f"    Test-case writer: {test_cases.get('writer', '?')} ({test_cases.get('writer_model', '?')})")
    log(f"    Scorer:           {scoring.get('scorer', '?')} ({scoring.get('scorer_model', '?')})")
    log(f"    Result destination: {results.get('destination', '?')}")


def _print_integration(item: dict, verbose: bool):
    package_ok = all(item["packages"].values())
    env_ok = all(item["env"].values())
    line = f"  {'*' if item['configured'] else ' '} {item['label']}: {'SDK installed' if package_ok else 'SDK missing'}, {'env ready' if env_ok else 'env missing'}"
    if item["configured"] and package_ok and env_ok:
        ok(line.strip())
    elif item["configured"]:
        warn(line.strip())
    else:
        log(line)
    if verbose:
        packages = ", ".join(f"{name}={'ok' if value else 'missing'}" for name, value in item["packages"].items())
        env = ", ".join(f"{name}={'set' if value else 'missing'}" for name, value in item["env"].items())
        log(f"      Purpose: {item['purpose']}")
        log(f"      Packages: {packages}")
        log(f"      Env: {env}")
        log(f"      Docs: {item['docs_url']}")


def _print_custom_metrics(config: dict):
    from eagle_eval.custom_scoring import check_custom_metrics

    statuses = check_custom_metrics(config, project_dir())
    if not statuses:
        return
    log("\n  Custom metrics:")
    for status in statuses:
        (ok if status.ok else warn)(f"{status.name}: {status.path}" + ("" if status.ok else f" ({status.error})"))


def _print_completed_eval_summary(config: dict):
    log("\n  What a completed eval gives you:")
    log("    - generated multilingual test cases under data/synthetic/")
    log("    - quality_report.json showing which test cases are ready")
    log("    - scored agent runs with per-language metrics")
    log("    - a regression decision when comparing prompt/model versions")
    if config and str(config.get("results", {}).get("destination", "")).strip().lower() == "local":
        local_dir = config.get("results", {}).get("local", {}).get("directory", "data/results")
        log(f"    - local JSON and Markdown reports under {local_dir}/runs/")
    log("\n  To inspect configured services before live calls:")
    log("    - eagle-eval services --verbose")
