import json
from pathlib import Path

from click.testing import CliRunner

from eagle_eval.cli import cli
from tests.helpers import write_config


def test_run_dry_run_json_output_is_machine_readable(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))

        result = runner.invoke(cli, ["run", "--dry-run", "--languages", "en", "--json-output"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["dry_run"] is True
        assert payload["plan"]["languages"] == ["en"]


def test_status_json_output_is_machine_readable(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"), destination="local")

        result = runner.invoke(cli, ["status", "--dry-run", "--json-output"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["destination"] == "local"
        assert payload["dry_run"] is True


def test_scorer_test_json_output_is_machine_readable(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        write_config(Path("eval_config.yaml"))
        runner.invoke(cli, ["scorer", "init", "farmer_query_resolution", "--sample"])

        result = runner.invoke(
            cli,
            [
                "scorer", "test", "farmer_query_resolution",
                "--sample", "examples/scorer_sample.json", "--json-output",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["name"] == "farmer_query_resolution"
        assert payload["score"] == 1.0
