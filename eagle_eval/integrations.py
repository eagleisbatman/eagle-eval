"""Integration metadata and health checks for Eagle Eval."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass


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


def _has_package(package: str) -> bool:
    try:
        return importlib.util.find_spec(package) is not None
    except ModuleNotFoundError:
        return False


def _configured_keys(config: dict) -> set[str]:
    keys = set()
    test_cases = config.get("test_cases", {})
    scoring = config.get("scoring", {})
    results = config.get("results", {})

    for value in (
        test_cases.get("writer"),
        scoring.get("scorer"),
        results.get("destination"),
    ):
        if value:
            keys.add(str(value).strip().lower())

    return keys
