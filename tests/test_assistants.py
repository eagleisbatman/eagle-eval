from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli


def test_install_assistants_writes_codex_and_claude_helpers(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["install-assistants", "--yes"])
        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").exists()
        assert Path("CLAUDE.md").exists()
        assert Path(".codex/skills/eagle-eval/SKILL.md").exists()
        assert Path(".claude/skills/eagle-eval/SKILL.md").exists()
        agents_text = Path("AGENTS.md").read_text()
        codex_skill = Path(".codex/skills/eagle-eval/SKILL.md").read_text()
        claude_skill = Path(".claude/skills/eagle-eval/SKILL.md").read_text()
        assert "Test-case writer" in agents_text
        assert ".env.eagle-eval" in agents_text
        assert "Vertex AI Gemini" in agents_text
        assert "Amazon Bedrock Claude" in agents_text
        assert "Codex is the interface" in codex_skill
        assert ".env.eagle-eval" in codex_skill
        assert "Amazon Bedrock Claude" in codex_skill
        assert "eagle-eval doctor" in claude_skill
        assert ".env.eagle-eval" in claude_skill
        assert "Amazon Bedrock Claude" in claude_skill


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
