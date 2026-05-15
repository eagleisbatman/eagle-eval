"""Score whether the post is grounded in the research snapshot."""

from __future__ import annotations


def score(input, output, expected_output, metadata, context, metric=None):
    responses = output.get("responses", []) if isinstance(output, dict) else []
    post = str(responses[0]).lower() if responses else ""
    output_metadata = output.get("metadata", {}) if isinstance(output, dict) else {}
    sources = output_metadata.get("sources") or []
    provider_names = {str(source.get("provider", "")).lower() for source in sources}
    required_providers = {
        str(provider).lower()
        for provider in expected_output.get("required_source_providers", [])
    }
    aliases = {
        "openai": ("openai", "codex", "gpt"),
        "google": ("google", "gemini", "android"),
        "anthropic": ("anthropic", "claude"),
    }
    referenced_providers = set()
    for provider in provider_names:
        if any(alias in post for alias in aliases.get(provider, (provider,))):
            referenced_providers.add(provider)

    has_urls = all(str(source.get("url", "")).startswith("https://") for source in sources)
    has_required_sources = required_providers.issubset(provider_names)
    mentions_some_sources = bool(referenced_providers)
    value = sum([has_urls, has_required_sources, mentions_some_sources]) / 3
    return {
        "name": "source_grounding",
        "value": round(value, 3),
        "comment": (
            f"required={sorted(required_providers)}; "
            f"metadata_sources={sorted(provider_names)}; "
            f"mentioned={sorted(referenced_providers)}; "
            f"north_star={context['north_star']['name']}"
        ),
    }
