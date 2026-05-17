"""Provider calls used by synthetic data generation."""

from __future__ import annotations

import json
import logging
import time

from eagle_eval.providers import normalize_provider

log = logging.getLogger(__name__)


def call_generation_model(provider: str, model: str, prompt: str, retries: int = 3) -> dict | None:
    """Call the generation model. Supports Gemini, OpenAI, and Anthropic."""
    provider = normalize_provider(provider, model)
    for attempt in range(retries):
        try:
            if provider == "gemini":
                return _call_gemini(model, prompt)
            if provider == "openai":
                return _call_openai(model, prompt)
            if provider == "anthropic":
                return _call_anthropic(model, prompt)
            raise ValueError(f"Unsupported test-case writer: {provider}. Use gemini, openai, or anthropic.")
        except json.JSONDecodeError as exc:
            log.warning(f"JSON parse error on attempt {attempt + 1}: {exc}")
            time.sleep(2 ** attempt)
        except Exception as exc:
            log.warning(f"API error on attempt {attempt + 1}: {exc}")
            time.sleep(2 ** attempt)
    return None


def _call_gemini(model: str, prompt: str) -> dict:
    try:
        from google import genai

        client = genai.Client()
        response = client.models.generate_content(model=model, contents=prompt)
    except ImportError:
        from google.generativeai import GenerativeModel

        response = GenerativeModel(model).generate_content(prompt)
    return _parse_json_response(response.text)


def _call_openai(model: str, prompt: str) -> dict:
    from openai import OpenAI

    response = OpenAI().responses.create(model=model, input=prompt)
    return _parse_json_response(response.output_text)


def _call_anthropic(model: str, prompt: str) -> dict:
    import anthropic

    response = anthropic.Anthropic().messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json_response(response.content[0].text)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)
