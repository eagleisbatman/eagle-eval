import json
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli


def write_config(path: Path, language_count: int = 3):
    path.write_text(
        "\n".join(
            [
                "app_name: TestApp",
                "domain: agriculture",
                "user_persona: farmer",
                "app_context:",
                "  product: Agriculture advisory assistant",
                "  user: farmer",
                "  north_star:",
                "    name: monthly_unique_farmer_queries_resolved",
                "    definition: Farmer query resolved after safe answer or needed clarification.",
                "  resolution_policy:",
                "    answerable_now:",
                "      expectation: Answer directly with safe advice.",
                "    unclear_intent:",
                "      expectation: Ask a focused clarification question.",
                "agent:",
                "  module: tests.fake_agent",
                "  function: run_conversation",
                "domain_topics:",
                "  - crop disease",
                "languages:",
                f"  count: {language_count}",
                "  tier1:",
                "    - en",
                "  tier2:",
                "    - hi",
                "prompt_versions:",
                "  current:",
                "    router: 1",
                "test_cases:",
                "  writer: gemini",
                "  writer_model: gemini-2.0-flash",
                "  conversations_per_language: 1",
                "  turns_per_conversation: 3",
                "  max_concurrency: 1",
                "  quality_threshold: 3.5",
                "scoring:",
                "  scorer: gemini",
                "  scorer_model: gemini-3.1-pro",
                "  max_concurrency: 1",
                "  item_timeout_seconds: 120",
                "  regression_threshold: 0.05",
                "results:",
                "  destination: langfuse",
                "langfuse:",
                "  dataset_prefix: evals",
                "",
            ]
        )
    )


def test_run_dry_run_uses_current_directory_config(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["run", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "Agent: tests.fake_agent.run_conversation" in result.output
        assert "Dry run" in result.output


def test_gate_dry_run_does_not_mutate_conversations_or_write_report(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        conversation_path = data_dir / "en_conv_01.json"
        conversation = {
            "conversation_id": "en_conv_01",
            "language": "en",
            "language_name": "English",
            "primary_topic": "crop_disease",
            "difficulty_requested": "easy",
            "conversation_turns": [
                {"role": "user", "content": "My maize leaves have spots."},
                {"role": "user", "content": "What should I check first?"},
                {"role": "user", "content": "Can I treat it today?"},
            ],
        }
        conversation_path.write_text(json.dumps(conversation, indent=2))
        original = conversation_path.read_text()

        result = runner.invoke(cli, ["gate", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert conversation_path.read_text() == original
        assert not Path("data/synthetic/quality_report.json").exists()


def test_all_languages_respects_configured_language_count(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), language_count=4)

        result = runner.invoke(cli, ["generate", "--languages", "all", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "Languages: en, hi, sw, fr (4 total)" in result.output


def test_invalid_prompt_versions_returns_click_error(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["run", "--dry-run", "--prompt-versions", "not-json"])

        assert result.exit_code != 0
        assert "invalid JSON" in result.output
        assert "Traceback" not in result.output


def test_update_dry_run_prints_pip_upgrade_command(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "update",
                "--dry-run",
                "--source",
                "git+https://github.com/example/eagle-eval.git@main",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "pip install --upgrade" in result.output
        assert "github.com/example/eagle-eval.git@main" in result.output


def test_self_update_alias_is_not_registered():
    runner = CliRunner()

    result = runner.invoke(cli, ["self-update", "--help"])

    assert result.exit_code != 0
    assert "No such command 'self-update'" in result.output


def test_doctor_explains_config_roles(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["doctor"])

        assert result.exit_code == 0, result.output
        assert "App context:      Agriculture advisory assistant" in result.output
        assert "North Star:       monthly_unique_farmer_queries_resolved" in result.output
        assert "Test-case writer: gemini (gemini-2.0-flash)" in result.output
        assert "Scorer:" in result.output
        assert "Result destination: langfuse" in result.output
        assert "What a completed eval gives you" in result.output


def test_install_assistants_writes_codex_and_claude_helpers(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["install-assistants", "--yes"])

        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").exists()
        assert Path("CLAUDE.md").exists()
        assert Path(".claude/skills/eagle-eval/SKILL.md").exists()
        assert "Test-case writer" in Path("AGENTS.md").read_text()
        assert "eagle-eval doctor" in Path(".claude/skills/eagle-eval/SKILL.md").read_text()


def test_context_view_prints_app_context(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["context", "view"])

        assert result.exit_code == 0, result.output
        assert "Agriculture advisory assistant" in result.output
        assert "monthly_unique_farmer_queries_resolved" in result.output
        assert "unclear_intent" in result.output


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
                    "    return {",
                    "        'name': metric['name'],",
                    "        'value': 0.9,",
                    "        'comment': context['product'],",
                    "    }",
                    "",
                ]
            )
        )

        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text().replace(
                "  regression_threshold: 0.05\nresults:",
                "  regression_threshold: 0.05\n"
                "  custom_metrics:\n"
                "    - name: farmer_query_resolution\n"
                "      path: eval_scorers.farmer_resolution:score\n"
                "results:",
            )
        )

        from eagle_eval.config import load_config
        from eagle_eval.custom_scoring import load_custom_evaluators

        config = load_config(config_path)
        [evaluator] = load_custom_evaluators(config, Path.cwd())
        result = evaluator(input={}, output={}, expected_output={}, metadata={})

        assert result.name == "farmer_query_resolution"
        assert result.value == 0.9
        assert result.comment == "Agriculture advisory assistant"
