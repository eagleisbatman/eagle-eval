import json
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_doctor_explains_config_roles(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0, result.output
        assert "App context:      Agriculture advisory assistant" in result.output
        assert "North Star:       monthly_unique_farmer_queries_resolved" in result.output
        assert "Test-case writer: vertex (gemini-2.0-flash)" in result.output
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
        monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
        monkeypatch.setattr(integrations, "_has_package", lambda package: False)
        result = runner.invoke(cli, ["services"])
        assert result.exit_code == 0, result.output
        assert "Test-case writer: Vertex AI Gemini" in result.output
        assert "Scoring service: Vertex AI Gemini" in result.output
        assert "Result storage: Local files (ready)" in result.output
        assert "Missing SDK: google.genai" in result.output
        assert "Missing env: GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION" in result.output
        assert "Fix the setup items above" in result.output


def test_services_json_normalizes_anthropic_to_claude(tmp_path, monkeypatch):
    import eagle_eval.integrations as integrations

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="langfuse")
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text()
            .replace("  writer: vertex", "  writer: openai")
            .replace("  writer_model: gemini-2.0-flash", "  writer_model: gpt-4.1-mini")
            .replace("  scorer: vertex", "  scorer: anthropic")
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


def test_services_json_supports_bedrock_writer_and_scorer(tmp_path, monkeypatch):
    import eagle_eval.integrations as integrations

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        config_path = Path("eval_config.yaml")
        config_path.write_text(
            config_path.read_text()
            .replace("  writer: vertex", "  writer: bedrock")
            .replace("  writer_model: gemini-2.0-flash", "  writer_model: global.anthropic.claude-haiku-4-5-20251001-v1:0")
            .replace("  scorer: vertex", "  scorer: claude-bedrock")
            .replace("  scorer_model: gemini-3.1-pro", "  scorer_model: global.anthropic.claude-sonnet-4-5-20250929-v1:0")
        )
        monkeypatch.setattr(integrations, "_has_package", lambda package: package == "boto3")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        result = runner.invoke(cli, ["services", "--json-output"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload[0]["service"] == "bedrock"
        assert payload[0]["label"] == "Amazon Bedrock Claude"
        assert payload[0]["ready"] is True
        assert payload[1]["service"] == "bedrock"
        assert payload[1]["ready"] is True


def test_context_view_prints_app_context(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        result = runner.invoke(cli, ["context", "view"])
        assert result.exit_code == 0, result.output
        assert "Agriculture advisory assistant" in result.output
        assert "monthly_unique_farmer_queries_resolved" in result.output
        assert "unclear_intent" in result.output
