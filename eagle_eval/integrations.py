"""Integration metadata and health checks for Eagle Eval."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Integration:
    key: str
    label: str
    purpose: str
    packages: tuple[str, ...]
    env_vars: tuple[str, ...]
    docs_url: str


INTEGRATIONS = {
    "local": Integration(
        key="local",
        label="Local files",
        purpose="Store datasets, run JSON, and Markdown summaries on disk.",
        packages=(),
        env_vars=(),
        docs_url="README.md#local-results",
    ),
    "langfuse": Integration(
        key="langfuse",
        label="Langfuse",
        purpose="Store datasets, experiment runs, traces, and scores.",
        packages=("langfuse",),
        env_vars=("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"),
        docs_url="https://langfuse.com/docs/evaluation/overview",
    ),
    "langsmith": Integration(
        key="langsmith",
        label="LangSmith",
        purpose="Run experiments on datasets and inspect scores in LangSmith.",
        packages=("langsmith",),
        env_vars=("LANGSMITH_API_KEY",),
        docs_url="https://docs.langchain.com/langsmith/evaluation",
    ),
    "openai": Integration(
        key="openai",
        label="OpenAI",
        purpose="Create test cases, score outputs, and optionally use OpenAI Evals.",
        packages=("openai",),
        env_vars=("OPENAI_API_KEY",),
        docs_url="https://developers.openai.com/api/docs/guides/agent-evals",
    ),
    "gemini": Integration(
        key="gemini",
        label="Gemini",
        purpose="Create multilingual test cases and score outputs with Gemini.",
        packages=("google.genai",),
        env_vars=("GOOGLE_API_KEY",),
        docs_url="https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation",
    ),
    "vertex": Integration(
        key="vertex",
        label="Vertex AI evaluation",
        purpose="Use Google's Gen AI evaluation service for task-specific metrics.",
        packages=("vertexai",),
        env_vars=("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"),
        docs_url="https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation",
    ),
    "claude": Integration(
        key="claude",
        label="Claude",
        purpose="Create test cases and score outputs with Claude.",
        packages=("anthropic",),
        env_vars=("ANTHROPIC_API_KEY",),
        docs_url="https://platform.claude.com/docs/en/test-and-evaluate/develop-tests",
    ),
}

SERVICE_ALIASES = {
    "anthropic": "claude",
    "claude": "claude",
    "gemini": "gemini",
    "google": "gemini",
    "google-gemini": "gemini",
    "gpt": "openai",
    "langfuse": "langfuse",
    "langsmith": "langsmith",
    "local": "local",
    "openai": "openai",
    "vertex": "vertex",
    "vertexai": "vertex",
    "vertex-ai": "vertex",
}

ACTIVE_ROLE_SERVICES = {
    "test_case_writer": {"gemini", "openai", "claude"},
    "scoring_service": {"gemini", "openai", "claude"},
    "result_storage": {"local", "langfuse"},
}


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
    if "gemini" in model:
        return "gemini"
    if "claude" in model:
        return "claude"
    if model.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return "unknown"
