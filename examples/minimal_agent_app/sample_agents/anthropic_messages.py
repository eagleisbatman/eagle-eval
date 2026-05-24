"""Direct Anthropic Messages API sample wrapper for Eagle Eval.

This is not an agent framework; it is included because many Claude apps start
with the Anthropic SDK before adding their own tools or orchestration.

Install for live use:
    pip install anthropic
    Add ANTHROPIC_API_KEY to .env.eagle-eval.
"""

from __future__ import annotations

import os

from sample_agents.contract import as_eagle_eval_output, dependency_error, messages_to_text


def run_conversation(messages, language, prompt_versions=None):
    """Call Claude through the Anthropic Messages API and return Eagle Eval output."""
    try:
        import anthropic
    except ImportError as exc:
        raise dependency_error("anthropic", "pip install anthropic") from exc

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("EAGLE_EVAL_ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        max_tokens=1024,
        system=(
            "You are an agriculture advisory assistant. If key context is missing, "
            "ask one focused clarification question before recommending treatment."
        ),
        messages=[{"role": "user", "content": messages_to_text(messages)}],
    )
    text = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    )
    return as_eagle_eval_output(
        text,
        framework="anthropic_messages",
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
        },
    )
