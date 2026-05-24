"""Claude Code SDK sample wrapper for Eagle Eval.

Install for live use:
    pip install claude-code-sdk
    npm install -g @anthropic-ai/claude-code
    Add ANTHROPIC_API_KEY to .env.eagle-eval.
"""

from __future__ import annotations

import asyncio
import os

from sample_agents.contract import as_eagle_eval_output, dependency_error, messages_to_text


def run_conversation(messages, language, prompt_versions=None):
    """Run a Claude Code SDK agent and return Eagle Eval output."""
    response = asyncio.run(_run_claude_code(messages_to_text(messages)))
    return as_eagle_eval_output(
        response,
        framework="claude_code_sdk",
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
        },
    )


async def _run_claude_code(prompt: str) -> str:
    try:
        from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
    except ImportError as exc:
        raise dependency_error("claude-code-sdk", "pip install claude-code-sdk") from exc

    system_prompt = (
        "You are an agriculture advisory assistant. If key context is missing, "
        "ask one focused clarification question before recommending treatment."
    )
    async with ClaudeSDKClient(
        options=ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=int(os.environ.get("EAGLE_EVAL_CLAUDE_MAX_TURNS", "2")),
        )
    ) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if type(message).__name__ == "ResultMessage":
                return str(message.result)
            if hasattr(message, "content"):
                text_blocks = [
                    block.text
                    for block in message.content
                    if hasattr(block, "text")
                ]
                if text_blocks:
                    return "".join(text_blocks)
    return ""
