"""Claude Code SDK wrapper for the Twitter/X content sample.

Default mode is offline so Eagle Eval can run without credentials:
    EAGLE_EVAL_TWITTER_AGENT_MODE=offline

Live mode:
    pip install claude-code-sdk
    npm install -g @anthropic-ai/claude-code
    Add ANTHROPIC_API_KEY and EAGLE_EVAL_TWITTER_AGENT_MODE to .env.eagle-eval.
"""

from __future__ import annotations

import asyncio
import os

from sample_agents.contract import (
    as_eagle_eval_output,
    build_prompt,
    compose_offline_post,
    dependency_error,
    sdk_mode,
    source_payload,
)


def run_conversation(messages, language, prompt_versions=None):
    """Run the Claude Code SDK version of the content generator."""
    if sdk_mode() != "live":
        return compose_offline_post("claude_code_sdk", messages, language, prompt_versions)

    prompt = build_prompt(messages, language, prompt_versions)
    post = asyncio.run(_run_claude_code(prompt)).strip()
    return as_eagle_eval_output(
        post,
        framework="claude_code_sdk",
        tools_called=["load_research_brief", "claude_code_sdk_client"],
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
            "mode": "live",
            "post_character_count": len(post),
            "sources": source_payload(limit=3),
        },
    )


async def _run_claude_code(prompt: str) -> str:
    try:
        from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
    except ImportError as exc:
        raise dependency_error("claude-code-sdk", "pip install claude-code-sdk") from exc

    system_prompt = (
        "You write concise, sourced Twitter/X posts for AI builders. "
        "Stay under 280 characters and do not invent facts."
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
