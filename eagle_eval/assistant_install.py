"""Install project helper files for coding-agent workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallAction:
    path: Path
    status: str


def install_assistant_support(project_dir: Path, tool: str = "all", force: bool = False) -> list[InstallAction]:
    """Write Codex and Claude Code helper files into a project."""
    project_dir = project_dir.expanduser().resolve()
    actions: list[InstallAction] = []

    if tool in ("all", "codex"):
        actions.append(_write(project_dir / "AGENTS.md", _agents_md(), force=force))

    if tool in ("all", "claude"):
        actions.append(_write(project_dir / "CLAUDE.md", _claude_md(), force=force))
        actions.append(_write(project_dir / ".claude" / "skills" / "eagle-eval" / "SKILL.md", _claude_skill(), force=force))

    return actions


def _write(path: Path, content: str, force: bool) -> InstallAction:
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if existed and not force:
        return InstallAction(path=path, status="skipped")

    path.write_text(content.strip() + "\n", encoding="utf-8")
    return InstallAction(path=path, status="updated" if existed else "created")


def _agents_md() -> str:
    return """
# Eagle Eval Agent Guide

Use Eagle Eval when the user asks to create, check, run, compare, or explain agent evaluations.

## First Checks

- Run `eagle-eval doctor` before live runs so missing SDKs, keys, and config are visible.
- Run `eagle-eval context view` before judging quality so the app use case and North Star are visible.
- Use `eagle-eval generate --dry-run`, `eagle-eval gate --dry-run`, or `eagle-eval run --dry-run` before commands that call paid APIs or a real agent.
- Never overwrite generated data unless the user asks for it.

## Eval Flow

1. `eagle-eval generate --languages tier1` writes multilingual user test cases.
2. `eagle-eval gate` checks those cases and adds quality status.
3. `eagle-eval upload` stores passing cases in the configured result destination.
4. `eagle-eval run --languages tier1` runs the real agent and scores outputs.
5. `eagle-eval compare --baseline '{...}' --candidate '{...}'` catches regressions.

## Custom Scorers

- `eagle-eval scorer list` shows configured metrics and starter templates.
- `eagle-eval scorer init farmer_query_resolution --sample` creates a project-owned scorer.
- `eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json` runs the scorer locally.

## Product Vocabulary

- Test-case writer: the model service that creates eval conversations.
- Scorer: the model service or deterministic code that grades agent outputs.
- Result destination: where datasets, run output, score summaries, and debug context are stored. Local files are the default.
- App context: the app use case, user, North Star, and resolution policy that make scoring domain-specific.
- Custom metric: a developer-owned `module:function` scorer listed in `scoring.custom_metrics`.
"""


def _claude_md() -> str:
    return """
# Eagle Eval

This project uses Eagle Eval for local-first agent evaluation.

Run `/eagle-eval` in Claude Code for the project workflow. Use `eagle-eval doctor` first when you need to inspect SDKs, API keys, config roles, or next steps.

Key terms:
- Test-case writer: creates realistic multilingual eval cases.
- Scorer: grades the agent output using code checks or a stronger model.
- Result destination: stores datasets, run output, score summaries, and debug context. Local files are the default.
- App context: defines the product use case and North Star so scoring is not generic.
- Custom metric: a developer-owned scorer declared in `scoring.custom_metrics`.

Prefer dry runs before commands that call paid APIs or external services.
"""


def _claude_skill() -> str:
    return """
---
name: eagle-eval
description: Plan, run, and explain Eagle Eval workflows for this project
---

Use this skill whenever the user asks about agent evals, multilingual test cases, scoring, regressions, or Eagle Eval.

Workflow:
1. Inspect the current config with `eagle-eval doctor`.
2. Inspect the product use case with `eagle-eval context view`.
3. Explain what will happen before running commands that call APIs or the real agent.
4. Use dry-run commands first unless the user clearly asks for a live run.
5. Keep the user-facing outcome clear: generated test cases, quality report, scored runs, and regression comparison.

Commands:
- `eagle-eval doctor`
- `eagle-eval context view`
- `eagle-eval scorer list`
- `eagle-eval scorer init farmer_query_resolution --sample`
- `eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json`
- `eagle-eval generate --languages tier1`
- `eagle-eval gate`
- `eagle-eval upload`
- `eagle-eval run --languages tier1`
- `eagle-eval compare --baseline '{"router":13}' --candidate '{"router":14}'`

Scoring model:
- `language_consistency`: 0 or 1, based on whether the response language matches the test case.
- `response_completeness`: 0 to 1, based on how many turns received an answer.
- `topic_relevance`: 0 to 1, model-scored against the expected topic.
- `safety_check`: 0 or 1, model-scored for unsafe advice.
- `response_quality`: 0 to 1, model-scored for usefulness and actionability.
- `pass_rate`: 0 to 1, aggregate share of items passing all item checks.
"""
