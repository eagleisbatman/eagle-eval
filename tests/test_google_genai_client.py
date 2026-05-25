import sys
import types

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


def test_explicit_gemini_path_ignores_vertex_env(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["model"] = model
            captured["contents"] = contents
            return types.SimpleNamespace(text="ok")

    class FakeClient:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.models = FakeModels()

    genai_module = types.SimpleNamespace(Client=FakeClient)
    google_module = types.ModuleType("google")
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    assert generate_text("gemini-2.0-flash", "hello", use_vertex=False) == "ok"
    assert captured["kwargs"] == {}
