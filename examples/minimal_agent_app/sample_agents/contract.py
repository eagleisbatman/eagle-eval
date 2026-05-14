"""Helpers shared by the sample agent wrappers."""

from __future__ import annotations

from typing import Any


def messages_to_text(messages: list[dict[str, Any]]) -> str:
    """Flatten Eagle Eval conversation turns into a single prompt string."""
    lines = []
    for turn in messages:
        role = turn.get("role", "user")
        content = str(turn.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def as_eagle_eval_output(
    response: str,
    *,
    framework: str,
    tools_called: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Return the output shape Eagle Eval scorers expect."""
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
        f"Missing optional package '{package}'. Install it before using this "
        f"sample agent wrapper: {install_hint}"
    )
