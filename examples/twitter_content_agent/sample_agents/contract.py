"""Shared contract helpers for the Twitter/X content agent wrappers."""

from __future__ import annotations

import os
from typing import Any

from twitter_content_agent.research import research_context, source_payload


def messages_to_text(messages: list[dict[str, Any]]) -> str:
    lines = []
    for turn in messages:
        role = turn.get("role", "user")
        content = str(turn.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def sdk_mode() -> str:
    return os.environ.get("EAGLE_EVAL_TWITTER_AGENT_MODE", "offline").strip().lower()


def build_prompt(messages, language, prompt_versions=None) -> str:
    prompt_version_text = ", ".join(
        f"{name}=v{version}"
        for name, version in sorted((prompt_versions or {}).items())
    ) or "none"
    return "\n".join(
        [
            "You are a research-backed Twitter/X content generator for AI builders.",
            "Write one post under 280 characters.",
            "Use current GenAI updates from the research brief.",
            "Do not invent facts or URLs.",
            "Include one clear insight for builders, not generic hype.",
            f"Language: {language}",
            f"Prompt versions: {prompt_version_text}",
            "",
            "Research brief:",
            research_context(limit=3),
            "",
            "User request:",
            messages_to_text(messages),
        ]
    )


def compose_offline_post(framework: str, messages, language, prompt_versions=None) -> dict:
    """Deterministic content path used for CI and credential-free demos."""
    user_text = messages_to_text(messages).lower()
    if "investor" in user_text or "market" in user_text:
        post = (
            "This week's GenAI signal: distribution is the moat. Codex moves to phones, "
            "Gemini becomes an Android action layer, and Claude packages workflows for SMBs. "
            "Builders should test outcomes, not demos."
        )
    else:
        post = (
            "GenAI is shifting from chat to embedded work: Codex on mobile, Gemini inside "
            "Android tasks, and Claude inside SMB/public-good workflows. Signal for builders: "
            "eval the workflow, not just the model."
        )
    return as_eagle_eval_output(
        post,
        framework=framework,
        tools_called=["load_research_brief", "compose_twitter_post"],
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
            "mode": "offline",
            "post_character_count": len(post),
            "sources": source_payload(limit=3),
        },
    )


def as_eagle_eval_output(
    response: str,
    *,
    framework: str,
    tools_called: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    return {
        "responses": [response],
        "tools_called": tools_called or [],
        "metadata": {
            "framework": framework,
            **(metadata or {}),
        },
    }


def dependency_error(package: str, install_hint: str) -> RuntimeError:
    return RuntimeError(
        f"Missing optional package '{package}'. Install it before using live mode: {install_hint}"
    )

