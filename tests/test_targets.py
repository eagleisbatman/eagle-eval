from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_run_dry_run_applies_named_eval_target(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        _append_target(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["run", "--dry-run", "--target", "research"])

        assert result.exit_code == 0, result.output
        assert "Eval target: research" in result.output
        assert "Agent: app.research.run_research" in result.output
        assert "Run prefix: research" in result.output


def test_unknown_eval_target_returns_actionable_error(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        _append_target(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["run", "--dry-run", "--target", "missing"])

        assert result.exit_code != 0
        assert "Unknown eval target 'missing'" in result.output
        assert "research" in result.output


def _append_target(path: Path):
    path.write_text(
        path.read_text()
        + "\n".join(
            [
                "eval_targets:",
                "  - name: research",
                "    agent:",
                "      module: app.research",
                "      function: run_research",
                "    app_context:",
                "      north_star:",
                "        name: high_quality_research_briefs",
                "",
            ]
        )
    )
