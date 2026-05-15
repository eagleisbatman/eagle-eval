import importlib
import json
import shutil
import sys
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli


def test_twitter_content_agent_sample_runs_all_sdk_wrappers(tmp_path):
    sample_dir = Path(__file__).resolve().parents[1] / "examples" / "twitter_content_agent"
    project_dir = tmp_path / "twitter_content_agent"
    shutil.copytree(sample_dir, project_dir)
    runner = CliRunner()
    upload = runner.invoke(cli, ["--project-dir", str(project_dir), "upload", "--languages", "en", "--recreate"])
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
            ["--project-dir", str(project_dir), "run", "--languages", "en", "--agent-module", module, "--run-prefix", prefix],
        )
        assert result.exit_code == 0, result.output
        assert "twitter_post_quality" in result.output
        assert "source_grounding" in result.output
    assert len(sorted((project_dir / "data/results/runs").glob("*.json"))) == 3


def test_minimal_agent_app_runs_local_quickstart(tmp_path):
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]
    project_dir = tmp_path / "minimal_agent_app"
    shutil.copytree(repo_root / "examples" / "minimal_agent_app", project_dir)

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
    project_dir = Path(__file__).resolve().parents[1] / "examples" / "minimal_agent_app"
    _clear_sample_agents()
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
        _clear_sample_agents()


def _clear_sample_agents():
    for loaded_name in list(sys.modules):
        if loaded_name == "sample_agents" or loaded_name.startswith("sample_agents."):
            del sys.modules[loaded_name]
