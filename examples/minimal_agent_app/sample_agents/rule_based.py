"""Offline deterministic agent used by the minimal quickstart."""

from __future__ import annotations

from sample_agents.contract import as_eagle_eval_output


def run_conversation(messages, language, prompt_versions=None):
    """Return a deterministic response in the Eagle Eval output shape."""
    return as_eagle_eval_output(
        (
            "Please confirm the crop, your location, when the yellowing started, "
            "and whether the leaves have spots or pests before spraying."
        ),
        framework="rule_based",
        metadata={
            "language": language,
            "prompt_versions": prompt_versions or {},
        },
    )
