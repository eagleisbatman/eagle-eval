"""CLI entry point. Commands live in eagle_eval.commands."""

from pathlib import Path

import click

from eagle_eval import __version__
from eagle_eval.commands import register_commands
from eagle_eval.env_loader import load_env_files


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
    """Goal-first eval runner for AI agents.

    Run 'init' first to create eval_config.yaml, then generate → gate → upload → run.
    """
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = (project_dir or Path.cwd()).expanduser().resolve()
    ctx.obj["env_files"] = load_env_files(ctx.obj["project_dir"])


register_commands(cli)
