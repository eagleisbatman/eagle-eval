"""OpenAI Agents SDK wrapper for the Twitter/X content sample.

Default mode is offline so Eagle Eval can run without credentials:
    EAGLE_EVAL_TWITTER_AGENT_MODE=offline

Live mode:
    pip install openai-agents
    export OPENAI_API_KEY=...
    export EAGLE_EVAL_TWITTER_AGENT_MODE=live
"""

from __future__ import annotations

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
    """Run the OpenAI Agents SDK version of the content generator."""
    if sdk_mode() != "live":
        return compose_offline_post("openai_agents", messages, language, prompt_versions)

    try:
        from agents import Agent, Runner
    except ImportError as exc:
        raise dependency_error("openai-agents", "pip install openai-agents") from exc

    agent = Agent(
        name="Eagle Eval Twitter Content Agent",
        model=os.environ.get("EAGLE_EVAL_OPENAI_AGENT_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You write concise, sourced Twitter/X posts for AI builders. "
            "Stay under 280 characters and do not invent facts."
        ),
    )
    result = Runner.run_sync(agent, build_prompt(messages, language, prompt_versions))
    post = str(result.final_output).strip()
    return as_eagle_eval_output(
        post,
        framework="openai_agents",
        tools_called=["load_research_brief", "openai_agents_runner"],
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
            "mode": "live",
            "post_character_count": len(post),
            "sources": source_payload(limit=3),
        },
    )

