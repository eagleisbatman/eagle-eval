"""Provider-backed LLM judge calls."""

from __future__ import annotations

import json
import logging
import random
import time

from eagle_eval.providers import normalize_provider

log = logging.getLogger(__name__)


def judge_response(prompt: str, scorer: str | None, scorer_model: str, retries: int = 3) -> dict:
    """Call the scoring model and parse a JSON score response."""
    provider = normalize_provider(scorer, scorer_model or "")
    for attempt in range(retries):
        try:
            if provider == "gemini":
                text = _call_gemini(prompt, scorer_model)
            elif provider == "openai":
                text = _call_openai(prompt, scorer_model)
            elif provider == "anthropic":
                text = _call_anthropic(prompt, scorer_model)
            else:
                return {"score": 0.0, "reasoning": f"Unsupported scorer service: {provider}"}
            return _parse_json(text)
        except Exception as exc:
            log.warning(f"Scorer call attempt {attempt + 1} failed: {exc}")
            if attempt < retries - 1:
                time.sleep(retry_delay(attempt))
    return {"score": 0.0, "reasoning": "Scorer failed after retries"}


def retry_delay(attempt: int, base_seconds: float = 1.0, max_seconds: float = 30.0) -> float:
    """Return exponential retry delay with bounded jitter."""
    exponential = min(max_seconds, base_seconds * (2 ** attempt))
    jitter = random.uniform(0, min(base_seconds, 1.0))
    return exponential + jitter


def _call_gemini(prompt: str, scorer_model: str) -> str:
    try:
        from google import genai

        response = genai.Client().models.generate_content(model=scorer_model, contents=prompt)
    except ImportError:
        from google.generativeai import GenerativeModel

        response = GenerativeModel(scorer_model).generate_content(prompt)
    return response.text


def _call_openai(prompt: str, scorer_model: str) -> str:
    from openai import OpenAI

    return OpenAI().responses.create(model=scorer_model, input=prompt).output_text


def _call_anthropic(prompt: str, scorer_model: str) -> str:
    import anthropic

    response = anthropic.Anthropic().messages.create(
        model=scorer_model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text.strip())
