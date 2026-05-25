import json
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_local_run_preserves_agent_output_when_evaluator_fails(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        _write_agent()
        _write_failing_scorer()
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text()
            .replace("  module: tests.fake_agent", "  module: app.agent")
            .replace(
                "  regression_threshold: 0.05\nresults:",
                "  regression_threshold: 0.05\n  custom_metrics:\n    - name: broken_metric\n      path: eval_scorers.broken:score\nresults:",
            )
        )
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        (data_dir / "en_conv_01.json").write_text(json.dumps(_conversation()))
        result = runner.invoke(cli, ["run", "--languages", "en"])
        assert result.exit_code == 0, result.output

        report = json.loads(next(Path("data/results/runs").glob("*.json")).read_text())
        item = report["items"][0]
        assert item["output"]["responses"] == ["Which crop stage is the maize in?"]
        assert any(evaluation["name"] == "evaluation_error" for evaluation in item["evaluations"])
        assert not any(evaluation["name"] == "run_error" for evaluation in item["evaluations"])


def test_local_run_terminates_item_after_timeout(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        _write_sleeping_agent()
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text()
            .replace("  module: tests.fake_agent", "  module: app.agent")
            .replace("  item_timeout_seconds: 120", "  item_timeout_seconds: 1")
        )
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        (data_dir / "en_conv_01.json").write_text(json.dumps(_conversation()))

        result = runner.invoke(cli, ["run", "--languages", "en"])

        assert result.exit_code == 0, result.output
        report = json.loads(next(Path("data/results/runs").glob("*.json")).read_text())
        item = report["items"][0]
        assert item["output"]["error"] == "Exceeded item_timeout_seconds=1"
        assert item["evaluations"][0]["name"] == "item_timeout"


def _conversation() -> dict:
    return {
        "conversation_id": "en_conv_01",
        "language": "en",
        "language_name": "English",
        "primary_topic": "crop_disease",
        "quality_status": "passed",
        "scenario": "missing_critical_context",
        "expected_next_action": "ask_clarification",
        "required_clarification_slots": ["crop stage"],
        "resolution_goal": "Ask for crop stage before giving crop disease advice.",
        "conversation_turns": [{"role": "user", "content": "My maize leaves have yellow spots."}],
    }


def _write_agent():
    app_dir = Path("app")
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "agent.py").write_text(
        "def run_conversation(messages, language, prompt_versions=None):\n"
        "    return {'responses': ['Which crop stage is the maize in?'], 'metadata': {}}\n"
    )


def _write_failing_scorer():
    scorer_dir = Path("eval_scorers")
    scorer_dir.mkdir()
    (scorer_dir / "__init__.py").write_text("")
    (scorer_dir / "broken.py").write_text(
        "def score(input, output, expected_output, metadata, context, metric):\n"
        "    raise RuntimeError('scorer exploded')\n"
    )


def _write_sleeping_agent():
    app_dir = Path("app")
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "agent.py").write_text(
        "import time\n"
        "def run_conversation(messages, language, prompt_versions=None):\n"
        "    time.sleep(30)\n"
        "    return {'responses': ['too late'], 'metadata': {}}\n"
    )
