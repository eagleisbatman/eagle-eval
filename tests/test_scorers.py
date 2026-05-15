from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_custom_metric_receives_app_context(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        scorer_dir = Path("eval_scorers")
        scorer_dir.mkdir()
        (scorer_dir / "__init__.py").write_text("")
        (scorer_dir / "farmer_resolution.py").write_text(
            "\n".join(
                [
                    "def score(input, output, expected_output, metadata, context, metric):",
                    "    assert context['north_star']['name'] == 'monthly_unique_farmer_queries_resolved'",
                    "    return {'name': metric['name'], 'value': 0.9, 'comment': context['product']}",
                    "",
                ]
            )
        )
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text().replace(
                "  regression_threshold: 0.05\nresults:",
                "  regression_threshold: 0.05\n  custom_metrics:\n    - name: farmer_query_resolution\n      path: eval_scorers.farmer_resolution:score\nresults:",
            )
        )
        from eagle_eval.config import load_config
        from eagle_eval.custom_scoring import load_custom_evaluators

        [evaluator] = load_custom_evaluators(load_config(config_path), Path.cwd())
        result = evaluator(input={}, output={}, expected_output={}, metadata={})
        assert result.name == "farmer_query_resolution"
        assert result.value == 0.9
        assert result.comment == "Agriculture advisory assistant"


def test_scorer_init_creates_template_and_sample(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["scorer", "init", "farmer_query_resolution", "--sample"])
        assert result.exit_code == 0, result.output
        scorer_path = Path("eval_scorers/farmer_query_resolution.py")
        sample_path = Path("examples/scorer_sample.json")
        assert scorer_path.exists()
        assert sample_path.exists()
        assert "def score(" in scorer_path.read_text()
        assert "farmer_query_resolution" in result.output


def test_scorer_list_shows_templates_and_configured_metrics(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        result = runner.invoke(cli, ["scorer", "list"])
        assert result.exit_code == 0, result.output
        assert "No custom metrics configured" in result.output
        assert "farmer_query_resolution" in result.output
        assert "safe_actionability" in result.output


def test_scorer_test_runs_template_metric(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        init_result = runner.invoke(cli, ["scorer", "init", "farmer_query_resolution", "--sample"])
        assert init_result.exit_code == 0, init_result.output
        result = runner.invoke(
            cli,
            ["scorer", "test", "farmer_query_resolution", "--sample", "examples/scorer_sample.json"],
        )
        assert result.exit_code == 0, result.output
        assert "Scorer Test" in result.output
        assert "farmer_query_resolution" in result.output
        assert "Score:   1.000" in result.output
