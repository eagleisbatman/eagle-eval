"""OpenAI Agents SDK sample wrapper for Eagle Eval.

Install for live use:
    pip install openai-agents
    export OPENAI_API_KEY=...
"""

from __future__ import annotations

import os

from sample_agents.contract import as_eagle_eval_output, dependency_error, messages_to_text


def run_conversation(messages, language, prompt_versions=None):
    """Run an OpenAI Agents SDK agent and return Eagle Eval output."""
    try:
        from agents import Agent, Runner
    except ImportError as exc:
        raise dependency_error("openai-agents", "pip install openai-agents") from exc

    agent = Agent(
        name="Eagle Eval Sample Advisor",
        model=os.environ.get("EAGLE_EVAL_OPENAI_AGENT_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You are an agriculture advisory assistant. If key context is missing, "
            "ask one focused clarification question before recommending treatment."
        ),
    )
    result = Runner.run_sync(agent, messages_to_text(messages))
    return as_eagle_eval_output(
        str(result.final_output),
        framework="openai_agents",
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
        },
    )
