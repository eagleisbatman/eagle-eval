"""Optional model-judged goal achievement evaluator."""

from __future__ import annotations

import json

from eagle_eval.evaluation_types import Evaluation
from eagle_eval.llm_judge import judge_response
from eagle_eval.providers import infer_provider

_SCORER_MODEL = ""
_SCORER = None
_DOMAIN = ""
_APP_CONTEXT = {}


def configure_goal_judge(
    scorer_model: str,
    domain: str,
    scorer: str | None = None,
    app_context: dict | None = None,
):
    """Set model judge context from the main evaluator configuration."""
    global _SCORER_MODEL, _SCORER, _DOMAIN, _APP_CONTEXT
    _SCORER_MODEL = scorer_model
    _SCORER = scorer or infer_provider(scorer_model)
    _DOMAIN = domain
    _APP_CONTEXT = app_context or {}


def goal_achievement_judge(*, input, output, expected_output, metadata, **kwargs):
    """Ask the configured scorer model whether the output achieved the case goal."""
    goal = expected_output.get("resolution_goal")
    expected_action = metadata.get("expected_next_action") or expected_output.get("expected_next_action")
    if not goal and not expected_action:
        return Evaluation("goal_achievement_judge", None, "No resolution goal configured")

    prompt = f"""You are judging whether an AI agent achieved a specific eval case goal.
Score only this case. Return 1.0 for fully achieved, 0.5 for partially achieved, 0.0 for not achieved.

Domain: {_DOMAIN}
App context:
{_context_summary()}

Scenario: {metadata.get("scenario") or expected_output.get("scenario")}
Expected next action: {expected_action}
Required clarification slots: {json.dumps(expected_output.get("required_clarification_slots") or [], ensure_ascii=False)}
Resolution goal: {goal}

User messages:
{json.dumps(input.get("conversation_turns", []), ensure_ascii=False)[:3000]}

Agent output:
{json.dumps(output, ensure_ascii=False)[:3000]}

Judge whether the output satisfies the resolution goal and expected next action.
Respond ONLY with JSON: {{"score": 0.0, "reasoning": "..."}}"""

    result = judge_response(prompt, scorer=_SCORER, scorer_model=_SCORER_MODEL)
    return Evaluation("goal_achievement_judge", result["score"], result.get("reasoning", ""))


def _context_summary() -> str:
    if not _APP_CONTEXT:
        return "No app context configured."
    summary = {
        "product": _APP_CONTEXT.get("product"),
        "user": _APP_CONTEXT.get("user"),
        "north_star": _APP_CONTEXT.get("north_star"),
        "resolution_policy": _APP_CONTEXT.get("resolution_policy"),
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)
