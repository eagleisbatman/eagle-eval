import json
import importlib
import shutil
import sys
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli


def write_config(path: Path, language_count: int = 3, destination: str = "local"):
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
                f"  destination: {destination}",
                "  local:",
                "    directory: data/results",
                "    include_model_scorers: false",
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


def test_run_dry_run_can_override_agent_without_editing_config(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(
            cli,
            [
                "run",
                "--dry-run",
                "--agent-module",
                "sample_agents.openai_agents",
                "--agent-function",
                "run_conversation",
                "--run-prefix",
                "openai-agents",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Agent: sample_agents.openai_agents.run_conversation" in result.output
        assert "Run prefix: openai-agents" in result.output


def test_init_dry_run_defaults_to_local_results(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init", "--dry-run"], input="\n" * 40)

        assert result.exit_code == 0, result.output
        assert "destination: local" in result.output
        assert "directory: data/results" in result.output
        assert "include_model_scorers: false" in result.output


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
        assert "Result destination: local" in result.output
        assert "local JSON and Markdown reports under data/results/runs/" in result.output
        assert "What a completed eval gives you" in result.output
        assert "eagle-eval services --verbose" in result.output


def test_services_shows_configured_roles_and_missing_setup(tmp_path, monkeypatch):
    import eagle_eval.integrations as integrations

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setattr(integrations, "_has_package", lambda package: False)

        result = runner.invoke(cli, ["services"])

        assert result.exit_code == 0, result.output
        assert "Test-case writer: Gemini" in result.output
        assert "Scoring service: Gemini" in result.output
        assert "Result storage: Local files (ready)" in result.output
        assert "Missing SDK: google.genai" in result.output
        assert "Missing env: GOOGLE_API_KEY" in result.output
        assert "Fix the setup items above" in result.output


def test_services_json_normalizes_anthropic_to_claude(tmp_path, monkeypatch):
    import eagle_eval.integrations as integrations

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="langfuse")
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text()
            .replace("  writer: gemini", "  writer: openai")
            .replace("  writer_model: gemini-2.0-flash", "  writer_model: gpt-4.1-mini")
            .replace("  scorer: gemini", "  scorer: anthropic")
            .replace("  scorer_model: gemini-3.1-pro", "  scorer_model: claude-sonnet-4-5")
        )
        monkeypatch.setattr(integrations, "_has_package", lambda package: True)
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test")
        monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        result = runner.invoke(cli, ["services", "--json-output"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload[0]["service"] == "openai"
        assert payload[0]["ready"] is True
        assert payload[1]["service"] == "claude"
        assert payload[1]["label"] == "Claude"
        assert payload[1]["ready"] is True
        assert payload[2]["service"] == "langfuse"
        assert payload[2]["ready"] is True


def test_install_assistants_writes_codex_and_claude_helpers(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["install-assistants", "--yes"])

        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").exists()
        assert Path("CLAUDE.md").exists()
        assert Path(".codex/skills/eagle-eval/SKILL.md").exists()
        assert Path(".claude/skills/eagle-eval/SKILL.md").exists()
        assert "Test-case writer" in Path("AGENTS.md").read_text()
        assert "Codex is the interface" in Path(".codex/skills/eagle-eval/SKILL.md").read_text()
        assert "eagle-eval doctor" in Path(".claude/skills/eagle-eval/SKILL.md").read_text()


def test_install_assistants_can_install_only_codex_project_skill(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["install-assistants", "--tool", "codex", "--yes"])

        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").exists()
        assert Path(".codex/skills/eagle-eval/SKILL.md").exists()
        assert not Path("CLAUDE.md").exists()
        assert not Path(".claude/skills/eagle-eval/SKILL.md").exists()


def test_install_assistants_can_install_global_skills(tmp_path, monkeypatch):
    runner = CliRunner()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["install-assistants", "--scope", "global", "--yes"])

        assert result.exit_code == 0, result.output
        assert (home_dir / ".codex/skills/eagle-eval/SKILL.md").exists()
        assert (home_dir / ".claude/skills/eagle-eval/SKILL.md").exists()
        assert not Path("AGENTS.md").exists()
        assert not Path("CLAUDE.md").exists()
        assert "~/.codex/skills/eagle-eval/SKILL.md" in result.output
        assert "~/.claude/skills/eagle-eval/SKILL.md" in result.output


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
            [
                "scorer",
                "test",
                "farmer_query_resolution",
                "--sample",
                "examples/scorer_sample.json",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Scorer Test" in result.output
        assert "farmer_query_resolution" in result.output
        assert "Score:   1.000" in result.output


def test_local_upload_writes_dataset_file(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        (data_dir / "en_conv_01.json").write_text(
            json.dumps(
                {
                    "conversation_id": "en_conv_01",
                    "language": "en",
                    "language_name": "English",
                    "primary_topic": "crop_disease",
                    "quality_status": "passed",
                    "scenario": "missing_critical_context",
                    "expected_next_action": "ask_clarification",
                    "conversation_turns": [
                        {"role": "user", "content": "My maize leaves have yellow spots."}
                    ],
                }
            )
        )

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
        app_dir = Path("app")
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")
        (app_dir / "agent.py").write_text(
            "\n".join(
                [
                    "def run_conversation(messages, language, prompt_versions=None):",
                    "    return {'responses': ['Which crop stage is the maize in?'], 'metadata': {}}",
                    "",
                ]
            )
        )
        scorer_dir = Path("eval_scorers")
        scorer_dir.mkdir()
        (scorer_dir / "__init__.py").write_text("")
        (scorer_dir / "resolution.py").write_text(
            "\n".join(
                [
                    "def score(input, output, expected_output, metadata, context, metric):",
                    "    return {",
                    "        'name': metric['name'],",
                    "        'value': 0.8,",
                    "        'comment': context['north_star']['name'],",
                    "    }",
                    "",
                ]
            )
        )
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text().replace(
                "  module: tests.fake_agent",
                "  module: app.agent",
            ).replace(
                "  regression_threshold: 0.05\nresults:",
                "  regression_threshold: 0.05\n"
                "  custom_metrics:\n"
                "    - name: farmer_query_resolution\n"
                "      path: eval_scorers.resolution:score\n"
                "results:",
            )
        )
        data_dir = Path("data/synthetic/en")
        data_dir.mkdir(parents=True)
        (data_dir / "en_conv_01.json").write_text(
            json.dumps(
                {
                    "conversation_id": "en_conv_01",
                    "language": "en",
                    "language_name": "English",
                    "primary_topic": "crop_disease",
                    "quality_status": "passed",
                    "scenario": "missing_critical_context",
                    "expected_next_action": "ask_clarification",
                    "conversation_turns": [
                        {"role": "user", "content": "My maize leaves have yellow spots."}
                    ],
                }
            )
        )

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
        assert any(
            evaluation["name"] == "farmer_query_resolution"
            for evaluation in report["items"][0]["evaluations"]
        )


def test_twitter_content_agent_sample_runs_all_sdk_wrappers(tmp_path):
    sample_dir = Path(__file__).resolve().parents[1] / "examples" / "twitter_content_agent"
    project_dir = tmp_path / "twitter_content_agent"
    shutil.copytree(sample_dir, project_dir)
    runner = CliRunner()

    upload = runner.invoke(
        cli,
        [
            "--project-dir",
            str(project_dir),
            "upload",
            "--languages",
            "en",
            "--recreate",
        ],
    )
    assert upload.exit_code == 0, upload.output
    assert "Total items: 3" in upload.output

    wrappers = {
        "google-adk": "sample_agents.google_adk",
        "openai-agents": "sample_agents.openai_agents",
        "claude-code": "sample_agents.claude_code_sdk",
    }
    for prefix, module in wrappers.items():
        result = runner.invoke(
            cli,
            [
                "--project-dir",
                str(project_dir),
                "run",
                "--languages",
                "en",
                "--agent-module",
                module,
                "--run-prefix",
                prefix,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "twitter_post_quality" in result.output
        assert "source_grounding" in result.output

    run_reports = sorted((project_dir / "data/results/runs").glob("*.json"))
    assert len(run_reports) == 3


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


def test_minimal_agent_app_runs_local_quickstart(tmp_path):
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "examples" / "minimal_agent_app"
    project_dir = tmp_path / "minimal_agent_app"
    shutil.copytree(source, project_dir)

    services = runner.invoke(cli, ["--project-dir", str(project_dir), "services"])
    assert services.exit_code == 0, services.output
    assert "Result storage: Local files (ready)" in services.output

    upload = runner.invoke(cli, ["--project-dir", str(project_dir), "upload", "--languages", "en"])
    assert upload.exit_code == 0, upload.output
    assert (project_dir / "data/results/datasets/en_conversations.json").exists()

    run = runner.invoke(cli, ["--project-dir", str(project_dir), "run", "--languages", "en"])
    assert run.exit_code == 0, run.output
    assert "Local reports" in run.output
    reports = sorted((project_dir / "data/results/runs").glob("*.json"))
    assert reports
    payload = json.loads(reports[-1].read_text())
    assert payload["items"][0]["output"]["metadata"]["framework"] == "rule_based"

    status = runner.invoke(cli, ["--project-dir", str(project_dir), "status"])
    assert status.exit_code == 0, status.output
    assert "Local datasets: 1 file(s)" in status.output
    assert "Local runs: 1 JSON report(s)" in status.output


def test_minimal_agent_sdk_wrappers_are_importable():
    repo_root = Path(__file__).resolve().parents[1]
    project_dir = repo_root / "examples" / "minimal_agent_app"
    for loaded_name in list(sys.modules):
        if loaded_name == "sample_agents" or loaded_name.startswith("sample_agents."):
            del sys.modules[loaded_name]
    sys.path.insert(0, str(project_dir))
    try:
        for module_name in (
            "sample_agents.google_adk",
            "sample_agents.openai_agents",
            "sample_agents.claude_code_sdk",
            "sample_agents.anthropic_messages",
            "sample_agents.rule_based",
        ):
            module = importlib.import_module(module_name)
            assert callable(module.run_conversation)
    finally:
        sys.path.remove(str(project_dir))
        for loaded_name in list(sys.modules):
            if loaded_name == "sample_agents" or loaded_name.startswith("sample_agents."):
                del sys.modules[loaded_name]
