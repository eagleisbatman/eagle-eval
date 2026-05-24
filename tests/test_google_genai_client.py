import pytest

from eagle_eval.google_genai_client import generate_text, using_vertex_env


def test_vertex_mode_requires_vertex_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_GENAI_USE_VERTEXAI"):
        generate_text("gemini-2.0-flash", "hello", use_vertex=True)


def test_using_vertex_env_accepts_common_truthy_values(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    assert using_vertex_env() is True
