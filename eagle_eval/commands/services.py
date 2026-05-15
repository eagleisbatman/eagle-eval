"""Configured services command."""

import json

import click

from eagle_eval.cli_output import format_readiness_map, heading, log, ok, warn
from eagle_eval.cli_runtime import load_optional_config


@click.command("services")
@click.option("--json-output", is_flag=True, help="Print machine-readable service readiness")
@click.option("--verbose", is_flag=True, help="Show package, env, purpose, and docs details")
def services(json_output, verbose):
    """Show the services used for test writing, scoring, and result storage."""
    config = load_optional_config()
    if not config:
        if json_output:
            log("[]")
            return
        heading("Configured Services")
        warn("No eval_config.yaml found. Run 'eagle-eval init' first.")
        return

    from eagle_eval.integrations import check_configured_services

    statuses = check_configured_services(config)
    if json_output:
        log(json.dumps(statuses, indent=2, ensure_ascii=False))
        return

    heading("Configured Services")
    for status in statuses:
        _print_service(status, verbose)
    if all(status["ready"] for status in statuses):
        ok("\nAll configured services are ready for live commands.")
    else:
        warn("\nFix the setup items above before commands that call paid APIs or hosted services.")


def _print_service(status: dict, verbose: bool):
    state = "ready" if status["ready"] else ("planned" if not status["supported"] else "needs setup")
    marker = ok if status["ready"] else warn
    marker(f"{status['role']}: {status['label']} ({state})")
    if status.get("model"):
        log(f"    Model: {status['model']}")
    log(f"    Config value: {status.get('configured_as') or status['service']}")
    for issue in status["issues"]:
        log(f"    - {issue}")
    if verbose:
        packages = format_readiness_map(status["packages"], ok_label="ok", missing_label="missing")
        env = format_readiness_map(status["env"], ok_label="set", missing_label="missing")
        log(f"    Purpose: {status['purpose']}")
        log(f"    Packages: {packages or 'none required'}")
        log(f"    Env: {env or 'none required'}")
        log(f"    Docs: {status['docs_url'] or 'not available'}")
