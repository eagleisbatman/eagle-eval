from eagle_eval.providers import infer_provider, normalize_provider


def test_normalize_provider_aliases():
    assert normalize_provider("google", "unused") == "vertex"
    assert normalize_provider("google-gemini", "unused") == "vertex"
    assert normalize_provider("google-vertex", "unused") == "vertex"
    assert normalize_provider("vertex-ai", "unused") == "vertex"
    assert normalize_provider("gpt", "unused") == "openai"
    assert normalize_provider("claude", "unused") == "anthropic"
    assert normalize_provider("anthropic", "unused") == "anthropic"


def test_normalize_provider_infers_from_model_when_missing():
    assert normalize_provider(None, "gemini-3.1-pro") == "vertex"
    assert normalize_provider(None, "claude-sonnet-4-5") == "anthropic"
    assert normalize_provider(None, "gpt-4.1-mini") == "openai"
    assert normalize_provider(None, "o4-mini") == "openai"
    assert normalize_provider(None, "custom-model") == "unknown"


def test_infer_provider_is_single_canonical_mapping():
    assert infer_provider("gemini-2.0-flash") == "vertex"
    assert infer_provider("claude-haiku-4-5") == "anthropic"
    assert infer_provider("gpt-5.4") == "openai"
