from eagle_eval.run_health import report_run_errors, run_error_summary


def test_summary_flags_fully_failed_language():
    results = {"scores": {"en": {"run_error": 0.0}}}
    summary = run_error_summary(results)
    assert summary == {"total": 1, "fully_failed": ["en"], "partial": []}


def test_summary_flags_partial_failure():
    results = {"scores": {"en": {"run_error": 0.0, "goal_achievement": 0.8}}}
    summary = run_error_summary(results)
    assert summary == {"total": 1, "fully_failed": [], "partial": ["en"]}


def test_total_failure_returns_true():
    results = {"scores": {"en": {"run_error": 0.0}, "sw": {"run_error": 0.0}}}
    assert report_run_errors(results) is True


def test_partial_failure_does_not_fail_run():
    results = {"scores": {"en": {"run_error": 0.0, "goal_achievement": 0.8}}}
    assert report_run_errors(results) is False


def test_one_language_failing_does_not_fail_whole_run():
    results = {"scores": {"en": {"run_error": 0.0}, "sw": {"goal_achievement": 0.9}}}
    assert report_run_errors(results) is False


def test_healthy_run_returns_false():
    results = {"scores": {"en": {"goal_achievement": 0.9, "next_action_match": 1.0}}}
    assert report_run_errors(results) is False


def test_empty_scores_returns_false():
    assert report_run_errors({"scores": {}}) is False
