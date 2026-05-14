"""Google ADK sample wrapper for Eagle Eval.

Install for live use:
    pip install google-adk
    export GOOGLE_API_KEY=...
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sample_agents.contract import as_eagle_eval_output, dependency_error, messages_to_text

try:
    from google.adk.agents.llm_agent import Agent
except ImportError:
    Agent = None


def _build_root_agent():
    if Agent is None:
        raise dependency_error("google-adk", "pip install google-adk")
    return Agent(
        model=os.environ.get("EAGLE_EVAL_GOOGLE_ADK_MODEL", "gemini-2.0-flash"),
        name="eagle_eval_sample_advisor",
        description="Answers agriculture advisory questions for Eagle Eval samples.",
        instruction=(
            "You are an agriculture advisory assistant. If key context is missing, "
            "ask one focused clarification question before recommending treatment."
        ),
    )


root_agent = _build_root_agent() if Agent is not None else None


def run_conversation(messages, language, prompt_versions=None):
    """Run a Google ADK agent and return Eagle Eval output."""
    prompt = messages_to_text(messages)
    response = asyncio.run(_run_adk(prompt))
    return as_eagle_eval_output(
        response,
        framework="google_adk",
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
        },
    )


async def _run_adk(prompt: str) -> str:
    if root_agent is None:
        raise dependency_error("google-adk", "pip install google-adk")

    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
    except ImportError as exc:
        raise dependency_error("google-adk", "pip install google-adk") from exc

    app_name = "eagle_eval_minimal_agent"
    user_id = "eagle_eval_user"
    session_id = f"eval-{uuid4().hex}"
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
    )
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or final_text
    return final_text
