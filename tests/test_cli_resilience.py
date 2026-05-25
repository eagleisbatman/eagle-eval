from pathlib import Path

import pytest
from click.testing import CliRunner

from eagle_eval.agent_calling import call_agent
from eagle_eval.cli import cli
from tests.helpers import write_config


def test_scorer_list_does_not_execute_custom_metric_imports(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        scorer_dir = Path("eval_scorers")
        scorer_dir.mkdir()
        (scorer_dir / "__init__.py").write_text("")
        (scorer_dir / "dangerous.py").write_text(
            "from pathlib import Path\n"
            "Path('metric_import_executed').write_text('boom')\n"
            "def score(input, output, expected_output, metadata, context, metric):\n"
            "    return 1.0\n"
        )
        _append_metric(Path("eval_config.yaml"), "danger", "eval_scorers.dangerous:score")

        result = runner.invoke(cli, ["scorer", "list"])

        assert result.exit_code == 0, result.output
        assert "danger" in result.output
        assert not Path("metric_import_executed").exists()


def test_status_reports_invalid_json_as_click_error(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        data_dir = Path("data/synthetic")
        data_dir.mkdir(parents=True)
        (data_dir / "manifest.json").write_text("{")

        result = runner.invoke(cli, ["status", "--dry-run"])

        assert result.exit_code != 0
        assert "Invalid manifest JSON" in result.output
        assert "Traceback" not in result.output


def test_scorer_sample_invalid_json_is_actionable(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        Path("bad-sample.json").write_text("{")

        result = runner.invoke(
            cli,
            ["scorer", "test", "farmer_query_resolution", "--sample", "bad-sample.json"],
        )

        assert result.exit_code != 0
        assert "Invalid scorer sample JSON" in result.output
        assert "Traceback" not in result.output


def test_run_without_eval_items_fails_before_empty_report(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        _write_agent()
        config_path = Path("eval_config.yaml")
        config_path.write_text(config_path.read_text().replace("  module: tests.fake_agent", "  module: app.agent"))

        result = runner.invoke(cli, ["run", "--languages", "en"])

        assert result.exit_code != 0
        assert "No eval items found" in result.output
        assert "eagle-eval generate" in result.output
        assert not Path("data/results/runs").exists()


def test_invalid_language_code_cannot_escape_data_directory(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["generate", "--languages", "../outside", "--dry-run"])

        assert result.exit_code != 0
        assert "Invalid language code" in result.output


def test_local_results_directory_must_stay_inside_project(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text().replace(
                "    directory: data/results",
                "    directory: ../outside-results",
            )
        )
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)

        result = runner.invoke(cli, ["upload", "--languages", "en"])

        assert result.exit_code != 0
        assert "results.local.directory must stay inside" in result.output


def test_plain_mode_uses_ascii_status_output(tmp_path, monkeypatch):
    monkeypatch.setenv("EAGLE_EVAL_PLAIN", "1")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["status", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "----------------------------------------------" in result.output
        assert "[WARN]" in result.output
        assert "⚠" not in result.output
        assert "─" not in result.output


def test_call_agent_uses_signature_without_retrying_internal_typeerror():
    calls = []

    def agent(messages, language, prompt_versions=None):
        calls.append((messages, language, prompt_versions))
        raise TypeError("agent body failed")

    with pytest.raises(TypeError, match="agent body failed"):
        call_agent(agent, {"conversation_turns": [{"role": "user"}], "language": "en"}, {"router": 1})

    assert len(calls) == 1


def test_call_agent_omits_prompt_versions_when_not_supported():
    def agent(messages, language):
        return {"responses": [f"{language}:{len(messages)}"]}

    result = call_agent(agent, {"conversation_turns": [1, 2], "language": "hi"}, {"router": 1})

    assert result["responses"] == ["hi:2"]


def _append_metric(config_path: Path, name: str, path: str):
    config_path.write_text(
        config_path.read_text().replace(
            "  regression_threshold: 0.05\nresults:",
            f"  regression_threshold: 0.05\n  custom_metrics:\n    - name: {name}\n      path: {path}\nresults:",
        )
    )


def _write_agent():
    app_dir = Path("app")
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "agent.py").write_text(
        "def run_conversation(messages, language, prompt_versions=None):\n"
        "    return {'responses': ['ok'], 'metadata': {}}\n"
    )
