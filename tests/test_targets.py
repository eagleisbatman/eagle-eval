from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from eagle_eval.target_compare import build_target_comparison
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


def test_compare_targets_dry_run_validates_target_plan(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        _append_targets(Path("eval_config.yaml"), ["orchestrator", "research"])

        result = runner.invoke(
            cli,
            [
                "compare-targets", "--orchestrator", "orchestrator",
                "--sub-targets", "research", "--languages", "en", "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Orchestrator: orchestrator" in result.output
        assert "Sub-targets: research" in result.output
        assert "Dry run" in result.output


def test_build_target_comparison_flags_weaker_orchestrator():
    comparison = build_target_comparison(
        {
            "orchestrator": {"summary": {"goal_achievement": {"rate": 0.4}}},
            "research": {"summary": {"goal_achievement": {"rate": 0.9}}},
        },
        "orchestrator",
        ["research"],
    )

    assert comparison["verdict"] == "needs_attention"
    assert comparison["gaps"][0]["target"] == "research"
    assert comparison["gaps"][0]["goal_achievement_delta"] == -0.5


def _append_target(path: Path, name: str = "research"):
    _append_targets(path, [name])


def _append_targets(path: Path, names: list[str]):
    path.write_text(
        path.read_text()
        + "\n".join(
            ["eval_targets:"]
            + [line for name in names for line in _target_lines(name)]
        )
    )


def _target_lines(name: str) -> list[str]:
    return [
        f"  - name: {name}",
        "    agent:",
        f"      module: app.{name}",
        f"      function: run_{name}",
        "    app_context:",
        "      north_star:",
        "        name: high_quality_research_briefs",
        "",
    ]
