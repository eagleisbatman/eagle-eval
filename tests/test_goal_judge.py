from eagle_eval.goal_judge import configure_goal_judge, goal_achievement_judge
from eagle_eval.goal_summary import build_goal_summary


def test_goal_achievement_judge_calls_configured_model(monkeypatch):
    calls = {}

    def fake_judge(prompt, scorer, scorer_model):
        calls["prompt"] = prompt
        calls["scorer"] = scorer
        calls["scorer_model"] = scorer_model
        return {"score": 0.5, "reasoning": "Partially met"}

    monkeypatch.setattr("eagle_eval.goal_judge.judge_response", fake_judge)
    configure_goal_judge(
        scorer="gemini",
        scorer_model="gemini-3.1-pro",
        domain="agriculture",
        app_context={"north_star": {"name": "queries_resolved"}},
    )

    evaluation = goal_achievement_judge(
        input={"conversation_turns": [{"role": "user", "content": "My crop is sick"}]},
        output={"responses": ["What crop stage is it?"]},
        expected_output={
            "scenario": "missing_critical_context",
            "expected_next_action": "ask_clarification",
            "resolution_goal": "Ask for crop stage before advising.",
        },
        metadata={},
    )

    assert evaluation.name == "goal_achievement_judge"
    assert evaluation.value == 0.5
    assert calls["scorer"] == "gemini"
    assert calls["scorer_model"] == "gemini-3.1-pro"
    assert "Resolution goal: Ask for crop stage" in calls["prompt"]


def test_goal_achievement_judge_skips_cases_without_goal_or_action():
    evaluation = goal_achievement_judge(input={}, output={}, expected_output={}, metadata={})

    assert evaluation.value is None
    assert "No resolution goal" in evaluation.comment


def test_goal_summary_includes_model_judge_when_present():
    summary = build_goal_summary(
        [
            {
                "metadata": {"conversation_id": "case-1", "scenario": "answerable_now"},
                "expected_output": {},
                "evaluations": [
                    {"name": "goal_achievement", "value": 1.0},
                    {"name": "goal_achievement_judge", "value": 0.5},
                    {"name": "next_action_match", "value": 1.0},
                ],
            }
        ]
    )

    assert summary["goal_achievement_judge"]["scored"] == 1
    assert summary["goal_achievement_judge"]["met"] == 1
    assert summary["scenarios"]["answerable_now"]["goal_achievement_judge"]["rate"] == 1.0
