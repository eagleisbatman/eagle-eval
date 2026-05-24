"""Google ADK wrapper for the Twitter/X content sample.

Default mode is offline so Eagle Eval can run without credentials:
    EAGLE_EVAL_TWITTER_AGENT_MODE=offline

Live mode:
    pip install google-adk
    Add GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION, and EAGLE_EVAL_TWITTER_AGENT_MODE to .env.eagle-eval.
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sample_agents.contract import (
    as_eagle_eval_output,
    build_prompt,
    compose_offline_post,
    dependency_error,
    sdk_mode,
    source_payload,
)


def run_conversation(messages, language, prompt_versions=None):
    """Run the Google ADK version of the content generator."""
    if sdk_mode() != "live":
        return compose_offline_post("google_adk", messages, language, prompt_versions)

    prompt = build_prompt(messages, language, prompt_versions)
    post = asyncio.run(_run_adk(prompt)).strip()
    return as_eagle_eval_output(
        post,
        framework="google_adk",
        tools_called=["load_research_brief", "google_adk_runner"],
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
            "mode": "live",
            "post_character_count": len(post),
            "sources": source_payload(limit=3),
        },
    )


async def _run_adk(prompt: str) -> str:
    try:
        from google.adk.agents.llm_agent import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
    except ImportError as exc:
        raise dependency_error("google-adk", "pip install google-adk") from exc

    root_agent = Agent(
        model=os.environ.get("EAGLE_EVAL_GOOGLE_ADK_MODEL", "gemini-2.0-flash"),
        name="eagle_eval_twitter_content_agent",
        description="Writes sourced Twitter/X posts about current GenAI updates.",
        instruction=(
            "You write concise, sourced Twitter/X posts for AI builders. "
            "Stay under 280 characters and do not invent facts."
        ),
    )
    app_name = "eagle_eval_twitter_content_agent"
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
