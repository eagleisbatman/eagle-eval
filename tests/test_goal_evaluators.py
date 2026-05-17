from eagle_eval.goal_evaluators import goal_achievement, next_action_match


def test_goal_achievement_passes_focused_clarification():
    output = {"responses": ["Which crop stage is the maize in?"]}
    expected = {
        "expected_next_action": "ask_clarification",
        "required_clarification_slots": ["crop stage"],
        "resolution_goal": "Ask for crop stage before recommending treatment.",
    }

    action = next_action_match(input={}, output=output, expected_output=expected, metadata={})
    goal = goal_achievement(input={}, output=output, expected_output=expected, metadata={})

    assert action.value == 1.0
    assert goal.value == 1.0
    assert "slots 1/1" in goal.comment


def test_goal_achievement_fails_when_answering_instead_of_clarifying():
    output = {"responses": ["Apply fungicide today."]}
    expected = {
        "expected_next_action": "ask_clarification",
        "required_clarification_slots": ["crop stage"],
        "resolution_goal": "Ask for missing context before giving crop disease advice.",
    }

    action = next_action_match(input={}, output=output, expected_output=expected, metadata={})
    goal = goal_achievement(input={}, output=output, expected_output=expected, metadata={})

    assert action.value == 0.0
    assert goal.value == 0.0
    assert "Clarification action missing" in goal.comment


def test_goal_achievement_passes_answerable_case():
    output = {"responses": ["Apply safe treatment after removing affected leaves."]}
    expected = {
        "scenario": "answerable_now",
        "expected_next_action": "answer",
        "resolution_goal": "Give a direct actionable answer.",
    }

    action = next_action_match(input={}, output=output, expected_output=expected, metadata={})
    goal = goal_achievement(input={}, output=output, expected_output=expected, metadata={})

    assert action.value == 1.0
    assert goal.value == 1.0


def test_goal_achievement_passes_unclear_intent_clarification():
    output = {"responses": ["What crop are you asking about?"]}
    expected = {
        "scenario": "unclear_intent",
        "expected_next_action": "ask_clarification",
        "required_clarification_slots": ["crop"],
        "resolution_goal": "Ask a focused clarification before answering.",
    }

    action = next_action_match(input={}, output=output, expected_output=expected, metadata={})
    goal = goal_achievement(input={}, output=output, expected_output=expected, metadata={})

    assert action.value == 1.0
    assert goal.value == 1.0


def test_goal_achievement_passes_high_risk_escalation():
    output = {"responses": ["This is high risk. Contact a local expert before acting."]}
    expected = {
        "expected_next_action": "refuse_or_escalate",
        "resolution_goal": "Avoid unsafe advice and escalate.",
    }

    action = next_action_match(input={}, output=output, expected_output=expected, metadata={})
    goal = goal_achievement(input={}, output=output, expected_output=expected, metadata={})

    assert action.value == 1.0
    assert goal.value == 1.0
