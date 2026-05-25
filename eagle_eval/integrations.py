"""Integration metadata and health checks for Eagle Eval."""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from eagle_eval.integration_registry import ACTIVE_ROLE_SERVICES, INTEGRATIONS, SERVICE_ALIASES


def check_integrations(config: dict | None = None) -> list[dict]:
    """Return install/env status for known integrations."""
    configured = _configured_keys(config or {})
    results = []
    for integration in INTEGRATIONS.values():
        results.append(
            {
                "key": integration.key,
                "label": integration.label,
                "purpose": integration.purpose,
                "configured": integration.key in configured,
                "packages": {
                    package: _has_package(package)
                    for package in integration.packages
                },
                "env": {name: bool(os.environ.get(name)) for name in integration.env_vars},
                "docs_url": integration.docs_url,
            }
        )
    return results


def check_configured_services(config: dict) -> list[dict[str, Any]]:
    """Return readiness for the exact services configured for this project."""
    statuses = []
    for role in _configured_roles(config):
        integration = INTEGRATIONS.get(role["service"])
        if integration is None:
            statuses.append(
                {
                    **role,
                    "label": role["service"],
                    "purpose": "Unknown service.",
                    "packages": {},
                    "env": {},
                    "ready": False,
                    "supported": False,
                    "docs_url": "",
                    "issues": [f"Unknown service: {role['configured_as']}"],
                }
            )
            continue

        packages = {
            package: _has_package(package)
            for package in integration.packages
        }
        env = {name: bool(os.environ.get(name)) for name in integration.env_vars}
        supported = role["service"] in ACTIVE_ROLE_SERVICES.get(role["role_key"], set())
        issues = []
        missing_packages = [name for name, ok in packages.items() if not ok]
        missing_env = [name for name, ok in env.items() if not ok]
        if missing_packages:
            issues.append("Missing SDK: " + ", ".join(missing_packages))
        if missing_env:
            issues.append("Missing env: " + ", ".join(missing_env))
        if not supported:
            issues.append("This service is planned for this role, not active yet.")

        statuses.append(
            {
                **role,
                "label": integration.label,
                "purpose": integration.purpose,
                "packages": packages,
                "env": env,
                "ready": not issues,
                "supported": supported,
                "docs_url": integration.docs_url,
                "issues": issues,
            }
        )
    return statuses


def normalize_service_key(value: str | None, model: str | None = None) -> str:
    """Normalize user-facing service names to Eagle Eval integration keys."""
    raw = (value or _infer_service_from_model(model or "")).strip().lower()
    return SERVICE_ALIASES.get(raw, raw)


def _has_package(package: str) -> bool:
    try:
        return importlib.util.find_spec(package) is not None
    except ModuleNotFoundError:
        return False


def _configured_keys(config: dict) -> set[str]:
    return {role["service"] for role in _configured_roles(config)}


def _configured_roles(config: dict) -> list[dict[str, Any]]:
    test_cases = config.get("test_cases", {})
    scoring = config.get("scoring", {})
    results = config.get("results", {})
    return [
        {
            "role_key": "test_case_writer",
            "role": "Test-case writer",
            "service": normalize_service_key(test_cases.get("writer"), test_cases.get("writer_model")),
            "configured_as": test_cases.get("writer"),
            "model": test_cases.get("writer_model"),
        },
        {
            "role_key": "scoring_service",
            "role": "Scoring service",
            "service": normalize_service_key(scoring.get("scorer"), scoring.get("scorer_model")),
            "configured_as": scoring.get("scorer"),
            "model": scoring.get("scorer_model"),
        },
        {
            "role_key": "result_storage",
            "role": "Result storage",
            "service": normalize_service_key(results.get("destination")),
            "configured_as": results.get("destination"),
            "model": None,
        },
    ]


def _infer_service_from_model(model: str) -> str:
    model = model.lower()
    if "anthropic.claude" in model:
        return "bedrock"
    if "gemini" in model:
        return "vertex"
    if "claude" in model:
        return "claude"
    if model.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return "unknown"
