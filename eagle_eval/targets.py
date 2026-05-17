"""Named eval target helpers."""

from __future__ import annotations

import copy


def apply_target(config: dict, target_name: str | None) -> tuple[dict, dict | None]:
    """Return a config copy with the named target overrides applied."""
    next_config = copy.deepcopy(config)
    if not target_name:
        return next_config, None

    target = _find_target(config, target_name)
    agent = target.get("agent", {})
    if agent.get("module"):
        next_config["agent"]["module"] = agent["module"]
    if agent.get("function"):
        next_config["agent"]["function"] = agent["function"]
    if target.get("app_context"):
        next_config["app_context"] = _deep_merge(next_config.get("app_context", {}), target["app_context"])
    return next_config, target


def target_names(config: dict) -> list[str]:
    return [str(target.get("name")) for target in config.get("eval_targets", []) if target.get("name")]


def _find_target(config: dict, target_name: str) -> dict:
    for target in config.get("eval_targets", []):
        if target.get("name") == target_name:
            return target
    names = ", ".join(target_names(config)) or "none configured"
    raise ValueError(f"Unknown eval target '{target_name}'. Available targets: {names}")


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
