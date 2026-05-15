"""Install project helper files for coding-agent workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eagle_eval.assistant_templates import agents_md, claude_md, claude_skill, codex_skill


@dataclass(frozen=True)
class InstallAction:
    path: Path
    status: str


def install_assistant_support(
    project_dir: Path,
    tool: str = "all",
    scope: str = "project",
    force: bool = False,
    home_dir: Path | None = None,
) -> list[InstallAction]:
    """Write Codex and Claude Code helper files."""
    project_dir = project_dir.expanduser().resolve()
    home_dir = (home_dir or Path.home()).expanduser().resolve()
    actions: list[InstallAction] = []

    if tool in ("all", "codex"):
        codex_root = project_dir / ".codex" if scope == "project" else home_dir / ".codex"
        actions.append(_write(codex_root / "skills" / "eagle-eval" / "SKILL.md", codex_skill(), force=force))
        if scope == "project":
            actions.append(_write(project_dir / "AGENTS.md", agents_md(), force=force))

    if tool in ("all", "claude"):
        claude_root = project_dir / ".claude" if scope == "project" else home_dir / ".claude"
        actions.append(_write(claude_root / "skills" / "eagle-eval" / "SKILL.md", claude_skill(), force=force))
        if scope == "project":
            actions.append(_write(project_dir / "CLAUDE.md", claude_md(), force=force))

    return actions


def _write(path: Path, content: str, force: bool) -> InstallAction:
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if existed and not force:
        return InstallAction(path=path, status="skipped")

    path.write_text(content.strip() + "\n", encoding="utf-8")
    return InstallAction(path=path, status="updated" if existed else "created")
