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
                "synthetic:",
                "  provider: gemini",
                "  model: gemini-2.0-flash",
                "  conversations_per_language: 1",
                "  turns_per_conversation: 3",
                "  max_concurrency: 1",
                "  quality_threshold: 3.5",
                "evaluation:",
                "  judge_provider: gemini",
                "  judge_model: gemini-3.1-pro",
                "  max_concurrency: 1",
                "  item_timeout_seconds: 120",
                "  regression_threshold: 0.05",
                "backends:",
                "  primary: langfuse",
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
