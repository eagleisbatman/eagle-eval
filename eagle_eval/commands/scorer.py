"""Custom scorer commands."""

import json
from pathlib import Path

import click

from eagle_eval.cli_output import heading, log, ok, warn
from eagle_eval.cli_runtime import load_config, load_optional_config, project_dir


@click.group("scorer")
def scorer_group():
    """Create, list, and test custom scorers."""


@scorer_group.command("list")
def scorer_list():
    """List configured custom scorers and built-in templates."""
    config = load_optional_config()
    from eagle_eval.custom_scoring import check_custom_metrics, configured_custom_metrics
    from eagle_eval.scorer_templates import SCORER_TEMPLATES

    heading("Custom Scorers")
    metrics = configured_custom_metrics(config)
    if metrics:
        statuses = {status.name: status for status in check_custom_metrics(config, project_dir())}
        for metric in metrics:
            status = statuses.get(metric["name"])
            suffix = _metric_status(metric, status)
            log(f"  - {metric['name']}: {metric['path']} ({suffix})")
    else:
        warn("No custom metrics configured in scoring.custom_metrics.")

    log("\n  Templates:")
    for name, template in SCORER_TEMPLATES.items():
        log(f"    - {name}: {template['description']}")


@scorer_group.command("init")
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite an existing scorer file")
@click.option("--sample", is_flag=True, help="Also write a sample scorer input JSON")
def scorer_init(name, force, sample):
    """Create a developer-owned scorer template."""
    from eagle_eval.scorer_templates import SCORER_TEMPLATES, write_sample_case, write_scorer_template

    if name not in SCORER_TEMPLATES:
        raise click.ClickException(f"Unknown scorer template '{name}'. Available: {', '.join(sorted(SCORER_TEMPLATES))}")

    heading("Create Custom Scorer")
    try:
        path = write_scorer_template(name, project_dir(), force=force)
    except FileExistsError as exc:
        raise click.ClickException(f"{exc} already exists. Use --force to overwrite.") from exc

    ok(f"Created {path.relative_to(project_dir())}")
    log("\n  Add this to eval_config.yaml under scoring.custom_metrics:")
    log("    - name: " + name)
    log("      path: " + SCORER_TEMPLATES[name]["path"])
    log("      weight: 0.45")
    log("      required: true")
    if sample:
        sample_path = write_sample_case(project_dir() / "examples" / "scorer_sample.json")
        ok(f"Created {sample_path.relative_to(project_dir())}")


@scorer_group.command("test")
@click.argument("name")
@click.option("--sample", "sample_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="JSON file with input/output/expected_output/metadata")
def scorer_test(name, sample_path):
    """Run one custom scorer locally against a sample JSON payload."""
    config = load_config()
    from eagle_eval.custom_scoring import load_custom_evaluator

    payload = _load_sample_payload(name, sample_path)
    evaluator = _load_evaluator(config, name)
    result = evaluator(
        input=payload.get("input", {}),
        output=payload.get("output", {}),
        expected_output=payload.get("expected_output", {}),
        metadata=payload.get("metadata", {}),
    )
    heading("Scorer Test")
    log(f"  Name:    {result.name}")
    log(f"  Score:   {result.value:.3f}")
    if result.comment:
        log(f"  Comment: {result.comment}")


def _metric_status(metric: dict, status) -> str:
    if not metric.get("enabled", True):
        return "disabled"
    return "ready" if status and status.ok else "not importable"


def _load_sample_payload(name: str, sample_path: Path | None) -> dict:
    from eagle_eval.scorer_templates import sample_case

    if sample_path:
        return json.loads(Path(sample_path).read_text(encoding="utf-8"))
    return sample_case(name)


def _load_evaluator(config: dict, name: str):
    from eagle_eval.custom_scoring import configured_custom_metrics, load_custom_evaluator
    from eagle_eval.scorer_templates import SCORER_TEMPLATES

    try:
        return load_custom_evaluator(config, project_dir(), name)
    except KeyError:
        metric = next((candidate for candidate in configured_custom_metrics(config) if candidate["name"] == name), None)
        if metric is None and name in SCORER_TEMPLATES:
            metric = {"name": name, "path": SCORER_TEMPLATES[name]["path"]}
        if metric is None:
            raise
        test_config = {**config, "scoring": {**config["scoring"], "custom_metrics": [{**metric, "enabled": True}]}}
        return load_custom_evaluator(test_config, project_dir(), name)
