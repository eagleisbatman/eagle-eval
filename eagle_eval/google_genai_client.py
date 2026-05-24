"""Google Gen AI client helpers for Gemini Developer API and Vertex AI."""

from __future__ import annotations

import os


def generate_text(model: str, prompt: str, *, use_vertex: bool = False) -> str:
    """Generate text with Google Gen AI, using Vertex AI when configured."""
    client_kwargs = _client_kwargs(use_vertex=use_vertex)
    from google import genai

    response = genai.Client(**client_kwargs).models.generate_content(model=model, contents=prompt)
    return response.text


def using_vertex_env() -> bool:
    return _env_truthy("GOOGLE_GENAI_USE_VERTEXAI")


def _client_kwargs(*, use_vertex: bool) -> dict:
    if not (use_vertex or using_vertex_env()):
        return {}

    _require_vertex_env()
    kwargs = {
        "vertexai": True,
        "project": os.environ["GOOGLE_CLOUD_PROJECT"],
        "location": os.environ["GOOGLE_CLOUD_LOCATION"],
    }
    try:
        from google.genai.types import HttpOptions

        kwargs["http_options"] = HttpOptions(api_version="v1")
    except ImportError:
        pass
    return kwargs


def _require_vertex_env() -> None:
    missing = []
    if not using_vertex_env():
        missing.append("GOOGLE_GENAI_USE_VERTEXAI")
    missing += [name for name in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION") if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Vertex AI Gemini requires env vars: " + ", ".join(missing))


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}
