"""Per-item local run scoring helpers."""

from __future__ import annotations

from eagle_eval.agent_calling import call_agent
from eagle_eval.evaluation_types import Evaluation


def safe_score_item(
    lang_code: str,
    item: dict,
    agent_fn,
    prompt_versions: dict,
    evaluators: list,
) -> tuple[dict, dict[str, float]]:
    try:
        return score_item(lang_code, item, agent_fn, prompt_versions, evaluators)
    except Exception as exc:
        return failed_item(lang_code, item, exc)


def score_item(
    lang_code: str,
    item: dict,
    agent_fn,
    prompt_versions: dict,
    evaluators: list,
) -> tuple[dict, dict[str, float]]:
    output = call_agent(agent_fn, item["input"], prompt_versions)
    evaluations = []
    score_values: dict[str, float] = {}
    for evaluator in evaluators:
        try:
            evaluation = evaluator(
                input=item["input"],
                output=output,
                expected_output=item["expected_output"],
                metadata=item["metadata"],
            )
        except Exception as exc:
            evaluation = Evaluation(
                name="evaluation_error",
                value=0.0,
                comment=f"{_evaluator_name(evaluator)} failed: {exc}",
            )
        evaluations.append(evaluation_payload(evaluation))
        if evaluation.value is not None:
            score_values[evaluation.name] = float(evaluation.value)
    return (
        item_payload(lang_code, item, output, evaluations),
        score_values,
    )


def failed_item(lang_code: str, item: dict, exc: Exception) -> tuple[dict, dict[str, float]]:
    evaluation = Evaluation(name="run_error", value=0.0, comment=str(exc))
    output = {"responses": [], "tools_called": [], "metadata": {}, "error": str(exc)}
    return (item_payload(lang_code, item, output, [evaluation_payload(evaluation)]), {"run_error": 0.0})


def item_payload(lang_code: str, item: dict, output: dict, evaluations: list[dict]) -> dict:
    return {
        "language": lang_code,
        "conversation_id": item.get("metadata", {}).get("conversation_id"),
        "input": item.get("input", {}),
        "expected_output": item.get("expected_output", {}),
        "metadata": item.get("metadata", {}),
        "output": output,
        "evaluations": evaluations,
    }


def evaluation_payload(evaluation) -> dict:
    return {
        "name": evaluation.name,
        "value": evaluation.value,
        "comment": evaluation.comment,
    }


def _evaluator_name(evaluator) -> str:
    return getattr(evaluator, "__name__", evaluator.__class__.__name__)
