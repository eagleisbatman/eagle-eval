"""Product context commands."""

import json

import click

from eagle_eval.cli_output import heading, log
from eagle_eval.cli_runtime import load_config


@click.group("context")
def context_group():
    """View the product context used by scorers."""


@context_group.command("view")
@click.option("--json-output", is_flag=True, help="Print the raw app_context JSON")
def context_view(json_output):
    """Show the app use case, North Star, and resolution policy."""
    config = load_config()
    app_context = config["app_context"]
    if json_output:
        log(json.dumps(app_context, indent=2, ensure_ascii=False))
        return

    north_star = app_context.get("north_star", {})
    heading("App Context")
    log(f"  Product:    {app_context.get('product', config.get('app_name'))}")
    log(f"  User:       {app_context.get('user', config.get('user_persona'))}")
    log(f"  North Star: {north_star.get('name')}")
    log(f"  Definition: {north_star.get('definition')}")
    _print_resolution_policy(app_context.get("resolution_policy", {}))


def _print_resolution_policy(policy: dict):
    if not policy:
        return
    log("\n  Resolution policy:")
    for scenario, details in policy.items():
        expectation = details.get("expectation") if isinstance(details, dict) else str(details)
        log(f"    - {scenario}: {expectation}")
