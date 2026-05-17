"""Model-scored quality review for generated conversations."""

from __future__ import annotations

import json
import logging

from eagle_eval.providers import normalize_provider

log = logging.getLogger(__name__)


def review_conversation(conv: dict, provider: str, model: str, domain: str, persona: str) -> dict | None:
    """Use LLM-as-a-judge to score conversation quality."""
    prompt = _quality_prompt(conv, domain, persona)
    try:
        provider = normalize_provider(provider, model)
        if provider == "gemini":
            return _call_gemini_judge(model, prompt)
        if provider == "openai":
            return _call_openai_judge(model, prompt)
        if provider == "anthropic":
            return _call_anthropic_judge(model, prompt)
        log.warning(f"Unsupported scorer service: {provider}")
        return None
    except Exception as exc:
        log.error(f"Quality review failed: {exc}")
        return None


def _quality_prompt(conv: dict, domain: str, persona: str) -> str:
    lang_name = conv.get("language_name", conv.get("language", "unknown"))
    topic = conv.get("primary_topic", "general")
    difficulty = conv.get("difficulty_requested", "medium")
    turns_json = json.dumps(conv.get("conversation_turns", []), ensure_ascii=False)[:3000]
    return f"""Review this synthetic conversation for quality. It should represent a {persona} asking about {topic} in {lang_name}.

Conversation turns (user messages only):
{turns_json}

Score each dimension 1-5:
- naturalness: Does this sound like a real person typing on a phone? Not overly formal or translated?
- topic_coverage: Does the conversation meaningfully explore the topic?
- difficulty_match: Does the actual difficulty match "{difficulty}"?
- language_quality: Is the {lang_name} natural and correct (not machine-translated English)?

Respond with ONLY this JSON, no markdown fences:
{{"naturalness": N, "topic_coverage": N, "difficulty_match": N, "language_quality": N, "overall": N, "issues": "description of any problems or empty string"}}"""


def _call_gemini_judge(model: str, prompt: str) -> dict:
    try:
        from google import genai

        response = genai.Client().models.generate_content(model=model, contents=prompt)
    except ImportError:
        from google.generativeai import GenerativeModel

        response = GenerativeModel(model).generate_content(prompt)
    return _parse_judge_response(response.text)


def _call_openai_judge(model: str, prompt: str) -> dict:
    from openai import OpenAI

    response = OpenAI().responses.create(model=model, input=prompt)
    return _parse_judge_response(response.output_text)


def _call_anthropic_judge(model: str, prompt: str) -> dict:
    import anthropic

    response = anthropic.Anthropic().messages.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_judge_response(response.content[0].text)


def _parse_judge_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text.strip())
