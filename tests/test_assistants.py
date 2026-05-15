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
