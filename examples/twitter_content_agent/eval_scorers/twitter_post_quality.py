"""Score whether the generated post is usable for Twitter/X."""

from __future__ import annotations


def score(input, output, expected_output, metadata, context, metric=None):
    responses = output.get("responses", []) if isinstance(output, dict) else []
    post = str(responses[0]).strip() if responses else ""
    output_metadata = output.get("metadata", {}) if isinstance(output, dict) else {}
    max_chars = int(expected_output.get("max_characters", 280))
    source_count = len(output_metadata.get("sources") or [])
    must_mention = expected_output.get("must_mention") or []

    checks = {
        "non_empty": bool(post),
        "under_limit": 0 < len(post) <= max_chars,
        "has_builder_takeaway": any(
            word in post.lower()
            for word in ("builder", "builders", "workflow", "eval", "outcome")
        ),
        "enough_sources": source_count >= int(expected_output.get("min_sources", 2)),
        "mentions_required": all(term.lower() in post.lower() for term in must_mention),
    }
    value = sum(1 for ok in checks.values() if ok) / len(checks)
    return {
        "name": "twitter_post_quality",
        "value": round(value, 3),
        "comment": (
            f"chars={len(post)}/{max_chars}; sources={source_count}; "
            f"north_star={context['north_star']['name']}; checks={checks}"
        ),
    }

