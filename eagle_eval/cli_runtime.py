"""Shared runtime helpers for Click commands."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click


def project_dir() -> Path:
    ctx = click.get_current_context(silent=True)
    if ctx and ctx.obj and ctx.obj.get("project_dir"):
        return ctx.obj["project_dir"]

    env_dir = os.environ.get("EAGLE_EVAL_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.cwd().resolve()


def config_path() -> Path:
    return project_dir() / "eval_config.yaml"


def data_dir() -> Path:
    return project_dir() / "data" / "synthetic"


def loaded_env_files() -> list:
    ctx = click.get_current_context(silent=True)
    if ctx and ctx.obj:
        return list(ctx.obj.get("env_files") or [])
    return []


def load_config() -> dict:
    from eagle_eval.config import load_config as load_config_file

    try:
        return load_config_file(config_path())
    except (FileNotFoundError, ValueError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc


def load_optional_config() -> dict:
    from eagle_eval.config import load_config as load_config_file

    try:
        return load_config_file(config_path())
    except (FileNotFoundError, ValueError, TypeError):
        return {}


def resolve_languages(config: dict, lang_arg: str) -> list[str]:
    langs = config["languages"]
    lang_arg = (lang_arg or "").strip().lower()
    if lang_arg == "tier1":
        resolved = langs.get("tier1", [])
    elif lang_arg == "tier2":
        resolved = langs.get("tier2", [])
    elif lang_arg == "all":
        resolved = all_configured_languages(config)
    else:
        resolved = [item.strip().lower() for item in lang_arg.split(",") if item.strip()]

    resolved = dedupe(resolved)
    if not resolved:
        raise click.ClickException(f"No languages resolved from '{lang_arg}'.")
    return resolved


def all_configured_languages(config: dict) -> list[str]:
    languages_path = project_dir() / "config" / "languages.json"
    if languages_path.exists():
        try:
            payload = json.loads(languages_path.read_text(encoding="utf-8"))
            return [item["code"] for item in payload if item.get("code")]
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise click.ClickException(f"Invalid languages file: {languages_path}: {exc}") from exc

    from eagle_eval.languages import ALL_LANGUAGES

    language_config = config["languages"]
    target_count = int(language_config.get("count") or 0)
    configured = dedupe(language_config.get("tier1", []) + language_config.get("tier2", []))
    target_count = max(target_count, len(configured))

    resolved = list(configured)
    for language in ALL_LANGUAGES:
        if len(resolved) >= target_count:
            break
        code = language["code"]
        if code not in resolved:
            resolved.append(code)
    return resolved


def dedupe(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = str(value).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def parse_json_object(value: str, option_name: str) -> dict:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"invalid JSON: {exc.msg}", param_hint=option_name) from exc

    if not isinstance(parsed, dict):
        raise click.BadParameter("must be a JSON object", param_hint=option_name)
    return parsed


def display_path(path: Path, project_root: Path, home_dir: Path) -> str:
    resolved = path.expanduser().resolve()
    for base, prefix in ((project_root, ""), (home_dir, "~/")):
        try:
            rel = resolved.relative_to(base)
            return f"{prefix}{rel}" if prefix else str(rel)
        except ValueError:
            continue
    return str(resolved)
