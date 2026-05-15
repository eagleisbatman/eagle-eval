"""Assistant helper installation command."""

from pathlib import Path

import click

from eagle_eval.cli_output import heading, log, ok, warn
from eagle_eval.cli_runtime import display_path, project_dir


@click.command("install-assistants")
@click.option("--tool", type=click.Choice(["all", "codex", "claude"]), default="all", show_default=True)
@click.option("--scope", type=click.Choice(["project", "global"]), default="project", show_default=True, help="Install into this project or the user's global skill directory")
@click.option("--yes", is_flag=True, help="Write files without asking for confirmation")
@click.option("--force", is_flag=True, help="Overwrite existing helper files")
def install_assistants(tool, scope, yes, force):
    """Install Codex and Claude Code helper files for this eval workflow."""
    root = project_dir()
    home_dir = Path.home().expanduser().resolve()
    heading("Install Assistant Helpers")
    log(f"  Project dir: {root}")
    log(f"  Target: {tool}")
    log(f"  Scope: {scope}")
    if scope == "global":
        log(f"  Home dir: {home_dir}")
    if not yes:
        target_description = "global skill files" if scope == "global" else "project helper files"
        if not click.confirm(f"  Write {target_description}?", default=True):
            log("  No files written.")
            return

    from eagle_eval.assistant_install import install_assistant_support

    actions = install_assistant_support(root, tool=tool, scope=scope, force=force, home_dir=home_dir)
    for action in actions:
        rel = display_path(action.path, root, home_dir)
        if action.status == "skipped":
            warn(f"Skipped existing {rel} (use --force to overwrite)")
        elif action.status == "updated":
            ok(f"Updated {rel}")
        else:
            ok(f"Created {rel}")
