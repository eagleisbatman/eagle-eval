import json
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_local_upload_writes_dataset_file(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        (data_dir / "en_conv_01.json").write_text(json.dumps(_conversation()))
        result = runner.invoke(cli, ["upload", "--languages", "en"])
        assert result.exit_code == 0, result.output
        dataset_path = Path("data/results/datasets/en_conversations.json")
        assert dataset_path.exists()
        payload = json.loads(dataset_path.read_text())
        assert payload[0]["expected_output"]["scenario"] == "missing_critical_context"


def test_local_run_writes_json_and_markdown_reports(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        _write_agent()
        _write_resolution_scorer()
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text()
            .replace("  module: tests.fake_agent", "  module: app.agent")
            .replace(
                "  regression_threshold: 0.05\nresults:",
                "  regression_threshold: 0.05\n  custom_metrics:\n    - name: farmer_query_resolution\n      path: eval_scorers.resolution:score\nresults:",
            )
        )
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        (data_dir / "en_conv_01.json").write_text(json.dumps(_conversation()))
        result = runner.invoke(cli, ["run", "--languages", "en", "--max-concurrency", "2"])
        assert result.exit_code == 0, result.output
        assert "Local reports" in result.output
        run_files = sorted(Path("data/results/runs").glob("*.json"))
        markdown_files = sorted(Path("data/results/runs").glob("*.md"))
        assert len(run_files) == 1
        assert len(markdown_files) == 1
        report = json.loads(run_files[0].read_text())
        assert report["destination"] == "local"
        assert report["settings"]["concurrency_requested"] == 2
        assert report["items"][0]["evaluations"]
        assert report["scores"]["en"]["farmer_query_resolution"] == 0.8
        assert any(evaluation["name"] == "farmer_query_resolution" for evaluation in report["items"][0]["evaluations"])


def test_local_status_reports_datasets_and_runs(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        datasets_dir = Path("data/results/datasets")
        runs_dir = Path("data/results/runs")
        datasets_dir.mkdir(parents=True)
        runs_dir.mkdir(parents=True)
        (datasets_dir / "en_conversations.json").write_text("[]")
        (runs_dir / "local-run.json").write_text(json.dumps({"scores": {}}))
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0, result.output
        assert "Local datasets: 1 file(s)" in result.output
        assert "Local runs: 1 JSON report(s)" in result.output


def _conversation() -> dict:
    return {
        "conversation_id": "en_conv_01",
        "language": "en",
        "language_name": "English",
        "primary_topic": "crop_disease",
        "quality_status": "passed",
        "scenario": "missing_critical_context",
        "expected_next_action": "ask_clarification",
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


def _write_resolution_scorer():
    scorer_dir = Path("eval_scorers")
    scorer_dir.mkdir()
    (scorer_dir / "__init__.py").write_text("")
    (scorer_dir / "resolution.py").write_text(
        "def score(input, output, expected_output, metadata, context, metric):\n"
        "    return {'name': metric['name'], 'value': 0.8, 'comment': context['north_star']['name']}\n"
    )
