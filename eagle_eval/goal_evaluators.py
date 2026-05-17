"""Goal-first deterministic evaluators."""

from __future__ import annotations

import re

from eagle_eval.evaluation_types import Evaluation


def next_action_match(*, input, output, expected_output, metadata, **kwargs):
    """Check whether the agent took the expected next action."""
    signals = _signals(output, expected_output, metadata)
    expected = signals["expected_next_action"]
    if not expected:
        return Evaluation("next_action_match", None, "No expected_next_action configured")

    observed = _observed_action(signals)
    matched = observed == expected
    return Evaluation(
        "next_action_match",
        1.0 if matched else 0.0,
        f"Expected {expected}, observed {observed}",
    )


def goal_achievement(*, input, output, expected_output, metadata, **kwargs):
    """Check whether the output satisfies the generated case goal."""
    signals = _signals(output, expected_output, metadata)
    goal = signals["resolution_goal"]
    expected = signals["expected_next_action"]
    if not goal and not expected:
        return Evaluation("goal_achievement", None, "No resolution goal configured")
    if not signals["has_response"]:
        return Evaluation("goal_achievement", 0.0, "No agent response")

    value, reason = _goal_result(signals)
    if goal:
        reason = f"{reason}; goal={goal}"
    return Evaluation("goal_achievement", value, reason)


def _goal_result(signals: dict) -> tuple[float, str]:
    expected = signals["expected_next_action"]
    observed = _observed_action(signals)
    if expected == "ask_clarification":
        covered, total = _slot_coverage(signals["combined"], signals["required_slots"])
        slots_ok = total == 0 or covered == total
        action_ok = observed == "ask_clarification"
        return (
            1.0 if action_ok and slots_ok else 0.0,
            f"Clarification action {'matched' if action_ok else 'missing'}; slots {covered}/{total}",
        )
    if expected in {"answer", "confirm", "refuse_or_escalate"}:
        matched = observed == expected
        return 1.0 if matched else 0.0, f"Expected {expected}, observed {observed}"
    return 1.0 if signals["has_response"] else 0.0, "Response present"


def _signals(output: dict, expected_output: dict, metadata: dict) -> dict:
    combined = _combined_responses(output)
    lowered = combined.lower()
    return {
        "combined": lowered,
        "has_response": bool(combined.strip()),
        "asks_question": "?" in combined or _contains_any(lowered, _QUESTION_HINTS),
        "confirms": _contains_any(lowered, _CONFIRM_HINTS),
        "escalates": _contains_any(lowered, _ESCALATION_HINTS),
        "expected_next_action": metadata.get("expected_next_action") or expected_output.get("expected_next_action"),
        "required_slots": expected_output.get("required_clarification_slots") or [],
        "resolution_goal": expected_output.get("resolution_goal"),
    }


def _observed_action(signals: dict) -> str:
    if not signals["has_response"]:
        return "no_response"
    if signals["escalates"]:
        return "refuse_or_escalate"
    if signals["confirms"]:
        return "confirm"
    if signals["asks_question"]:
        return "ask_clarification"
    return "answer"


def _combined_responses(output: dict) -> str:
    responses = output.get("responses", []) if isinstance(output, dict) else []
    return " ".join(str(response) for response in responses if response)


def _slot_coverage(text: str, slots: list[str]) -> tuple[int, int]:
    if not slots:
        return 0, 0
    normalized_text = _normalize(text)
    hits = sum(1 for slot in slots if all(word in normalized_text for word in _normalize(slot).split()))
    return hits, len(slots)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value).lower())).strip()


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


_QUESTION_HINTS = ("which ", "what ", "where ", "when ", "how long", "can you tell", "please share")
_CONFIRM_HINTS = ("confirm", "do you mean", "is that correct", "is that right", "should i understand")
_ESCALATION_HINTS = ("extension officer", "agronomist", "doctor", "lawyer", "local expert", "emergency")
