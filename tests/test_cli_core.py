import json
import sys
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_run_dry_run_uses_current_directory_config(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        result = runner.invoke(cli, ["run", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "Agent: tests.fake_agent.run_conversation" in result.output
        assert "Dry run" in result.output


def test_run_dry_run_can_override_agent_without_editing_config(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        result = runner.invoke(
            cli,
            [
                "run", "--dry-run", "--agent-module", "sample_agents.openai_agents",
                "--agent-function", "run_conversation", "--run-prefix", "openai-agents",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Agent: sample_agents.openai_agents.run_conversation" in result.output
        assert "Run prefix: openai-agents" in result.output


def test_project_import_context_swaps_same_package_between_projects(tmp_path):
    from eagle_eval.imports import import_from_project

    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    for project, value in ((project_a, "A"), (project_b, "B")):
        package_dir = project / "sample_agents"
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text("")
        (package_dir / "helper.py").write_text(f"VALUE = {value!r}\n")
        (package_dir / "agent.py").write_text("from sample_agents.helper import VALUE\n")
    try:
        module_a = import_from_project(project_a, "sample_agents.agent")
        module_b = import_from_project(project_b, "sample_agents.agent")
    finally:
        for loaded_name in list(sys.modules):
            if loaded_name == "sample_agents" or loaded_name.startswith("sample_agents."):
                del sys.modules[loaded_name]

    assert module_a.VALUE == "A"
    assert module_b.VALUE == "B"
    assert str(project_a.resolve()) not in sys.path
    assert str(project_b.resolve()) not in sys.path


def test_llm_judge_retries_with_backoff_and_jitter(monkeypatch):
    import eagle_eval.llm_judge as llm_judge

    monkeypatch.setattr(
        llm_judge,
        "_call_openai",
        lambda prompt, model: (_ for _ in ()).throw(RuntimeError("rate limit")),
    )
    monkeypatch.setattr(llm_judge.random, "uniform", lambda start, end: 0.25)
    sleeps = []
    monkeypatch.setattr(llm_judge.time, "sleep", sleeps.append)
    result = llm_judge.judge_response("score this", scorer="openai", scorer_model="gpt-4.1-mini", retries=3)
    assert result == {"score": 0.0, "reasoning": "Scorer failed after retries"}
    assert sleeps == [1.25, 2.25]


def test_init_dry_run_defaults_to_local_results(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "destination: local" in result.output
        assert "directory: data/results" in result.output
        assert "include_model_scorers: false" in result.output


def test_init_full_keeps_interactive_questionnaire(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init", "--full", "--dry-run"], input="\n" * 40)
        assert result.exit_code == 0, result.output
        assert "app_name: MyApp" in result.output


def test_init_minimal_writes_harness_friendly_config(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "init", "--minimal", "--app-name", "Farm Copilot",
                "--domain", "agriculture", "--user-persona", "farmer",
                "--agent-module", "farm.agent", "--agent-function", "run",
                "--topics", "crop disease,pest control", "--languages", "en,hi",
            ],
        )
        assert result.exit_code == 0, result.output
        config_text = Path("eval_config.yaml").read_text()
        assert "app_name: Farm Copilot" in config_text
        assert "module: farm.agent" in config_text
        assert "function: run" in config_text
        assert "monthly_unique_farmer_queries_resolved" in config_text
        assert Path("config/languages.json").exists()


def test_doctor_guides_harness_setup_for_minimal_defaults(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["init", "--minimal"])
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0, result.output
        assert "Codex/Claude setup guidance" in result.output
        assert "Ask the user for the real app/product name" in result.output
        assert "app_context.product is still generic" in result.output
        assert "Confirm the real import path" in result.output


def test_gate_dry_run_does_not_mutate_conversations_or_write_report(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        conversation_path = data_dir / "en_conv_01.json"
        conversation = {"conversation_id": "en_conv_01", "language": "en", "language_name": "English", "primary_topic": "crop_disease", "difficulty_requested": "easy", "conversation_turns": [{"role": "user", "content": "My maize leaves have spots."}, {"role": "user", "content": "What should I check first?"}, {"role": "user", "content": "Can I treat it today?"}]}
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
        result = runner.invoke(cli, ["update", "--dry-run", "--source", "git+https://github.com/example/eagle-eval.git@main"])
        assert result.exit_code == 0, result.output
        assert "pip install --upgrade" in result.output
        assert "github.com/example/eagle-eval.git@main" in result.output


def test_self_update_alias_is_not_registered():
    result = CliRunner().invoke(cli, ["self-update", "--help"])
    assert result.exit_code != 0
    assert "No such command 'self-update'" in result.output
