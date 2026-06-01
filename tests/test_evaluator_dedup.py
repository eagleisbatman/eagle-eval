"""Guards for two report-consistency fixes.

1. A custom metric whose name matches a builtin must REPLACE the builtin, not
   run alongside it. When both ran, the per-item score dict kept the last
   evaluation while the goal summary read the first, so the headline table and
   the summary silently reported different numbers for the same metric name.

2. The goal summary must expose BOTH the mean and the pass-rate (fraction
   >= 0.5). For a continuous metric (e.g. a model judge) these differ, and
   reporting only one while the headline shows the other reads as a contradiction.
"""

from __future__ import annotations

from eagle_eval import evaluators
from eagle_eval.evaluation_types import Evaluation
from eagle_eval.goal_summary import build_goal_summary


def _named(name):
    def evaluator(*, input, output, expected_output, metadata, **kwargs):
        return Evaluation(name, 1.0, "custom")

    evaluator.__name__ = name
    return evaluator


def test_custom_metric_replaces_shadowed_builtin(monkeypatch):
    custom = _named("next_action_match")
    monkeypatch.setattr(evaluators, "_CUSTOM_EVALUATORS", [custom])

    chosen = evaluators.get_item_evaluators(include_model_scorers=True)
    next_action = [ev for ev in chosen if getattr(ev, "__name__", None) == "next_action_match"]

    assert len(next_action) == 1, "exactly one next_action_match must survive"
    assert next_action[0] is custom, "the custom metric must win over the builtin"


def test_unshadowed_builtins_are_kept(monkeypatch):
    monkeypatch.setattr(evaluators, "_CUSTOM_EVALUATORS", [_named("next_action_match")])
    names = {getattr(ev, "__name__", None) for ev in evaluators.get_item_evaluators()}
    assert "goal_achievement" in names, "builtins without a custom twin stay registered"


def test_goal_summary_reports_mean_distinct_from_pass_rate():
    # Three judged items: values 1.0, 0.4, 0.4 -> mean 0.6, but only 1/3 >= 0.5.
    items = [
        {
            "metadata": {"conversation_id": f"c{i}", "scenario": "answerable_now"},
            "expected_output": {},
            "evaluations": [{"name": "goal_achievement_judge", "value": v, "comment": ""}],
        }
        for i, v in enumerate((1.0, 0.4, 0.4))
    ]
    bucket = build_goal_summary(items)["goal_achievement_judge"]

    assert bucket["scored"] == 3
    assert bucket["mean"] == 0.6
    assert bucket["rate"] == round(1 / 3, 3)
    assert bucket["mean"] != bucket["rate"], "continuous metric: mean and pass-rate must both be visible"
