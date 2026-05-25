import os
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from eagle_eval.env_loader import load_env_files, parse_env_file
from tests.helpers import write_config


def test_parse_env_file_supports_quotes_export_and_comments(tmp_path):
    path = tmp_path / ".env.eagle-eval"
    path.write_text(
        "\n".join(
            [
                "# comment",
                "export GOOGLE_GENAI_USE_VERTEXAI=true",
                "GOOGLE_CLOUD_PROJECT='project-one'",
                'GOOGLE_CLOUD_LOCATION="us-central1"',
                "OPENAI_API_KEY=abc # inline comment",
            ]
        )
    )

    assert parse_env_file(path) == {
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
        "GOOGLE_CLOUD_PROJECT": "project-one",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "OPENAI_API_KEY": "abc",
    }


def test_load_env_files_project_specific_values_win(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shell")
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (home / ".eagle-eval").mkdir()
    (home / ".eagle-eval" / ".env").write_text("OPENAI_API_KEY=global\n")
    (project / ".env").write_text("OPENAI_API_KEY=project\n")
    (project / ".env.eagle-eval").write_text("OPENAI_API_KEY=eagle\n")

    statuses = load_env_files(project, home_dir=home)

    assert [status.path.name for status in statuses] == [".env", ".env", ".env.eagle-eval"]
    assert os.environ["OPENAI_API_KEY"] == "eagle"


def test_services_loads_project_eagle_eval_env(tmp_path, monkeypatch):
    import eagle_eval.integrations as integrations

    for name in ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(integrations, "_has_package", lambda package: True)

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        Path(".env.eagle-eval").write_text(
            "\n".join(
                [
                    "GOOGLE_GENAI_USE_VERTEXAI=true",
                    "GOOGLE_CLOUD_PROJECT=test-project",
                    "GOOGLE_CLOUD_LOCATION=us-central1",
                ]
            )
        )
        result = runner.invoke(cli, ["services", "--verbose"])

    assert result.exit_code == 0, result.output
    assert "Env files: .env.eagle-eval" in result.output
    assert "Test-case writer: Vertex AI Gemini (ready)" in result.output
