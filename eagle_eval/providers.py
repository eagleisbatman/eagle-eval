"""Provider-name routing shared by generation and judging paths."""

PROVIDER_ALIASES = {
    "google": "vertex",
    "google-gemini": "vertex",
    "google-vertex": "vertex",
    "vertex": "vertex",
    "vertexai": "vertex",
    "vertex-ai": "vertex",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "openai": "openai",
    "gpt": "openai",
}


def normalize_provider(provider: str | None, model: str) -> str:
    raw = (provider or infer_provider(model)).strip().lower()
    return PROVIDER_ALIASES.get(raw, raw)


def infer_provider(model: str) -> str:
    model = model.lower()
    if "gemini" in model:
        return "vertex"
    if "claude" in model:
        return "anthropic"
    if model.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return "unknown"
