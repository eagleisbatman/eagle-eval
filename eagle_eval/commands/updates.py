"""Self-update command."""

import os
import shlex
import subprocess
import sys

import click

from eagle_eval import __version__
from eagle_eval.cli_output import heading, log, warn
from eagle_eval.cli_runtime import config_path, load_optional_config, project_dir


@click.command("update")
@click.option("--source", default=None, help="pip install target, e.g. package name or git+https URL")
@click.option("--pre", is_flag=True, help="Allow prerelease versions")
@click.option("--yes", is_flag=True, help="Skip confirmation for non-default update sources")
@click.option("--dry-run", is_flag=True, help="Print the update command without running it")
@click.option("--verbose", is_flag=True, help="Show update source resolution details")
def update(source, pre, yes, dry_run, verbose):
    """Upgrade Eagle Eval via pip."""
    config = load_optional_config()
    source = source or os.environ.get("EAGLE_EVAL_UPDATE_SOURCE") or config.get("updates", {}).get("source") or "eagle-eval"
    _validate_source(source)
    command = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if pre:
        command.append("--pre")
    command.append(source)

    heading("Eagle Eval Update")
    log(f"  Current version: {__version__}")
    log(f"  Update source: {source}")
    if verbose:
        log(f"  Project dir: {project_dir()}")
        log(f"  Config path: {config_path()}")
    log("\n  Command:")
    log(f"    {shlex.join(command)}")
    if dry_run:
        warn("\nDry run — update command was not executed")
        return
    if source != "eagle-eval" and not yes:
        if not click.confirm("  Continue with this non-default update source?", default=False):
            warn("\nUpdate cancelled")
            return
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"Update failed with exit code {exc.returncode}") from exc


def _validate_source(source: str) -> None:
    source = str(source).strip()
    if not source:
        raise click.ClickException("Update source cannot be empty")
    if source.startswith("-"):
        raise click.ClickException("Update source cannot start with '-'")
