"""Local result destination for running evals without a hosted service."""

from __future__ import annotations

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_local_experiment(
    config: dict,
    lang_codes: list[str],
    prompt_versions: dict,
    concurrency: int,
    project_dir: Path,
    run_prefix: str = "",
    verbose: bool = False,
) -> dict:
    """Run the real agent against local datasets and write JSON/Markdown reports."""
    from eagle_eval.custom_scoring import load_custom_evaluators
    from eagle_eval.evaluators import configure as configure_evaluators, get_item_evaluators
    from eagle_eval.imports import project_import_context

    project_dir = project_dir.expanduser().resolve()
    with project_import_context(project_dir, config["agent"]["module"]):
        local_config = config.get("results", {}).get("local", {})
        include_model_scorers = bool(local_config.get("include_model_scorers", False))
        results_dir = local_results_dir(config, project_dir)
        runs_dir = results_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        scorer = config["scoring"].get("scorer")
        scorer_model = config["scoring"]["scorer_model"]
        custom_evaluators = load_custom_evaluators(config, project_dir)
        configure_evaluators(
            scorer_model=scorer_model,
            scorer=scorer,
            domain=config["domain"],
            app_context=config["app_context"],
            custom_evaluators=custom_evaluators,
        )
        evaluators = get_item_evaluators(include_model_scorers=include_model_scorers)
        agent_fn = _load_agent(config)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        pv_str = "-".join(f"{key}v{value}" for key, value in sorted(prompt_versions.items()))
        run_name = "-".join(part for part in [run_prefix, "local", pv_str, timestamp] if part)

        all_scores: dict[str, dict[str, float]] = {}
        item_results = []

        for lang_code in lang_codes:
            lang_items = _load_items(project_dir, config, lang_code)
            score_lists: dict[str, list[float]] = defaultdict(list)
            processed_items = _run_language_items(
                lang_code=lang_code,
                items=lang_items,
                agent_fn=agent_fn,
                prompt_versions=prompt_versions,
                evaluators=evaluators,
                concurrency=concurrency,
            )

            for item_result, score_values in processed_items:
                item_results.append(item_result)
                for score_name, value in score_values.items():
                    score_lists[score_name].append(value)

            all_scores[lang_code] = {
                name: round(sum(values) / len(values), 3)
                for name, values in sorted(score_lists.items())
                if values
            }

        report = {
            "run_name": run_name,
            "timestamp": timestamp,
            "destination": "local",
            "prompt_versions": prompt_versions,
            "scores": all_scores,
            "items": item_results,
            "settings": {
                "include_model_scorers": include_model_scorers,
                "concurrency_requested": concurrency,
            },
        }

        json_path = runs_dir / f"{run_name}.json"
        markdown_path = runs_dir / f"{run_name}.md"
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        markdown_path.write_text(_markdown_report(report), encoding="utf-8")

        return {
            "scores": all_scores,
            "prompt_versions": prompt_versions,
            "timestamp": timestamp,
            "local_results": {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "items": len(item_results),
            },
        }


def _run_language_items(
    *,
    lang_code: str,
    items: list[dict],
    agent_fn,
    prompt_versions: dict,
    evaluators: list,
    concurrency: int,
) -> list[tuple[dict, dict[str, float]]]:
    max_workers = max(1, int(concurrency or 1))
    if max_workers == 1 or len(items) <= 1:
        return [
            _score_item(lang_code, item, agent_fn, prompt_versions, evaluators)
            for item in items
        ]

    ordered_results: list[tuple[dict, dict[str, float]] | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_score_item, lang_code, item, agent_fn, prompt_versions, evaluators): index
            for index, item in enumerate(items)
        }
        for future in as_completed(futures):
            ordered_results[futures[future]] = future.result()

    return [result for result in ordered_results if result is not None]


def _score_item(
    lang_code: str,
    item: dict,
    agent_fn,
    prompt_versions: dict,
    evaluators: list,
) -> tuple[dict, dict[str, float]]:
    output = _call_agent(agent_fn, item["input"], prompt_versions)
    evaluations = []
    score_values: dict[str, float] = {}
    for evaluator in evaluators:
        evaluation = evaluator(
            input=item["input"],
            output=output,
            expected_output=item["expected_output"],
            metadata=item["metadata"],
        )
        evaluations.append(_evaluation_payload(evaluation))
        if evaluation.value is not None:
            score_values[evaluation.name] = float(evaluation.value)

    return (
        {
            "language": lang_code,
            "conversation_id": item["metadata"].get("conversation_id"),
            "input": item["input"],
            "expected_output": item["expected_output"],
            "metadata": item["metadata"],
            "output": output,
            "evaluations": evaluations,
        },
        score_values,
    )


def write_local_datasets(
    config: dict,
    lang_codes: list[str],
    data_dir: Path,
    recreate: bool = False,
) -> dict:
    """Write local dataset JSON files from quality-gated conversations."""
    project_dir = data_dir.expanduser().resolve().parent.parent
    results_dir = local_results_dir(config, project_dir)
    datasets_dir = results_dir / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    results = {"datasets": {}, "total_items": 0}
    for lang_code in lang_codes:
        lang_dir = data_dir / lang_code
        items = [_conversation_to_item(lang_code, conv) for conv in _load_passed_conversations(lang_dir)]
        dataset_path = datasets_dir / f"{lang_code}_conversations.json"

        if dataset_path.exists() and not recreate:
            existing = json.loads(dataset_path.read_text(encoding="utf-8"))
            existing.extend(items)
            items = existing

        dataset_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        results["datasets"][str(dataset_path)] = len(items)
        results["total_items"] += len(items)

    return results


def local_results_dir(config: dict, project_dir: Path) -> Path:
    """Resolve the configured local results directory."""
    local_config = config.get("results", {}).get("local", {})
    configured = Path(str(local_config.get("directory", "data/results"))).expanduser()
    if configured.is_absolute():
        return configured
    return project_dir.expanduser().resolve() / configured


def _load_agent(config: dict):
    module_name = config["agent"]["module"]
    function_name = config["agent"]["function"]
    try:
        import importlib

        module = importlib.import_module(module_name)
        return getattr(module, function_name)
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"Cannot import agent: {module_name}.{function_name} — {exc}\n"
            "Make sure the agent module is importable from the eval project directory."
        ) from exc


def _call_agent(agent_fn, item_input: dict, prompt_versions: dict) -> dict:
    messages = item_input.get("conversation_turns", [])
    language = item_input.get("language", "en")
    try:
        result = agent_fn(messages=messages, language=language, prompt_versions=prompt_versions)
    except TypeError:
        result = agent_fn(messages=messages, language=language)

    if not isinstance(result, dict):
        return {"responses": [str(result)], "tools_called": [], "metadata": {}}
    return result


def _load_items(project_dir: Path, config: dict, lang_code: str) -> list[dict]:
    dataset_path = local_results_dir(config, project_dir) / "datasets" / f"{lang_code}_conversations.json"
    if dataset_path.exists():
        return json.loads(dataset_path.read_text(encoding="utf-8"))

    lang_dir = project_dir / "data" / "synthetic" / lang_code
    return [_conversation_to_item(lang_code, conv) for conv in _load_passed_conversations(lang_dir)]


def _load_passed_conversations(lang_dir: Path) -> list[dict]:
    conversations = []
    if not lang_dir.exists():
        return conversations

    for json_file in sorted(lang_dir.glob("*.json")):
        try:
            conv = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        status = conv.get("quality_status", "passed")
        if status in ("passed", "flagged"):
            conversations.append(conv)
    return conversations


def _conversation_to_item(lang_code: str, conv: dict) -> dict:
    turns = conv.get("conversation_turns", [])
    expected_output = {
        "expected_topics": conv.get("topic_tags", [conv.get("primary_topic", "general")]),
        "expected_language": lang_code,
        "min_turns_responded": max(1, int(len(turns) * 0.8)),
        "scenario": conv.get("scenario"),
        "expected_next_action": conv.get("expected_next_action"),
        "required_clarification_slots": conv.get("required_clarification_slots", []),
        "resolution_goal": conv.get("resolution_goal"),
    }
    expected_output.update(conv.get("expected_output") or {})
    return {
        "input": {
            "language": lang_code,
            "conversation_turns": turns,
        },
        "expected_output": expected_output,
        "metadata": {
            "language": lang_code,
            "language_name": conv.get("language_name", lang_code),
            "conversation_id": conv.get("conversation_id", "unknown"),
            "primary_topic": conv.get("primary_topic", "general"),
            "scenario": conv.get("scenario"),
            "expected_next_action": conv.get("expected_next_action"),
            "difficulty": conv.get("difficulty_actual", conv.get("difficulty_requested", "medium")),
            "quality_score": conv.get("quality_score"),
            "generated_by": conv.get("generated_by", "unknown"),
        },
    }


def _evaluation_payload(evaluation) -> dict:
    return {
        "name": evaluation.name,
        "value": evaluation.value,
        "comment": evaluation.comment,
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Eagle Eval Local Run: {report['run_name']}",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Items: `{len(report['items'])}`",
        f"- Model scorers included: `{report['settings']['include_model_scorers']}`",
        "",
        "## Scores",
        "",
        "| Language | Metric | Score |",
        "| --- | --- | ---: |",
    ]
    for language, scores in report["scores"].items():
        if not scores:
            lines.append(f"| {language} | no_scores | 0.000 |")
        for metric, score in scores.items():
            lines.append(f"| {language} | {metric} | {score:.3f} |")

    lines.extend(["", "## Items", ""])
    for item in report["items"]:
        lines.append(f"### {item['metadata'].get('conversation_id', 'unknown')}")
        lines.append("")
        for evaluation in item["evaluations"]:
            value = evaluation.get("value")
            value_text = f"{float(value):.3f}" if value is not None else "n/a"
            lines.append(f"- `{evaluation['name']}`: `{value_text}` {evaluation.get('comment', '')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
