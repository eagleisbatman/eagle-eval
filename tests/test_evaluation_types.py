"""Guards that eagle-eval owns its Evaluation type and never adopts a third
party's incompatible class based on what is installed.

Regression context: when ``langfuse`` was installed, ``evaluation_types`` used
to import ``langfuse.Evaluation`` (keyword-only), which crashed every grader
that constructs ``Evaluation`` positionally. The test env had no langfuse, so
the existing grader tests only ever exercised the fallback and missed it. These
tests inject a langfuse stand-in so the failure mode is reproduced regardless of
the local environment.
"""

from __future__ import annotations

import importlib
import sys
import types


def test_evaluation_supports_positional_and_keyword_construction():
    from eagle_eval.evaluation_types import Evaluation

    positional = Evaluation("goal_achievement", 1.0, "ok")
    keyword = Evaluation(name="goal_achievement", value=1.0, comment="ok")

    for ev in (positional, keyword):
        assert ev.name == "goal_achievement"
        assert ev.value == 1.0
        assert ev.comment == "ok"


def test_evaluation_value_defaults_to_none_skip_signal():
    from eagle_eval.evaluation_types import Evaluation

    ev = Evaluation("local_terminology")
    assert ev.value is None
    assert ev.comment == ""


def test_evaluation_is_eagle_eval_owned_not_third_party():
    from eagle_eval.evaluation_types import Evaluation

    assert Evaluation.__module__ == "eagle_eval.evaluation_types"


def test_evaluation_ignores_an_installed_langfuse(monkeypatch):
    """With a keyword-only ``langfuse.Evaluation`` present, eagle-eval must
    still expose its own positional-friendly class — never adopt langfuse's."""

    class _KeywordOnlyEvaluation:
        def __init__(self, *, name, value=None, comment=None):
            self.name, self.value, self.comment = name, value, comment

    fake_langfuse = types.ModuleType("langfuse")
    fake_langfuse.Evaluation = _KeywordOnlyEvaluation
    monkeypatch.setitem(sys.modules, "langfuse", fake_langfuse)

    module = importlib.reload(importlib.import_module("eagle_eval.evaluation_types"))
    try:
        # Would raise "takes 1 positional argument" if langfuse's class were adopted.
        ev = module.Evaluation("goal_achievement", 0.0, "still ours")
        assert ev.name == "goal_achievement"
        assert module.Evaluation is not _KeywordOnlyEvaluation
    finally:
        importlib.reload(importlib.import_module("eagle_eval.evaluation_types"))


def test_builtin_graders_construct_evaluation_without_raising():
    from eagle_eval.goal_evaluators import goal_achievement, next_action_match

    output = {"responses": ["Apply safe treatment after removing affected leaves."]}
    expected = {"scenario": "answerable_now", "expected_next_action": "answer"}

    action = next_action_match(input={}, output=output, expected_output=expected, metadata={})
    goal = goal_achievement(input={}, output=output, expected_output=expected, metadata={})

    assert action.name == "next_action_match"
    assert goal.name == "goal_achievement"
