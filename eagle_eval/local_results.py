"""Local result destination for running evals without a hosted service."""
from __future__ import annotations
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from eagle_eval.local_datasets import load_items, local_results_dir
from eagle_eval.local_reports import markdown_report


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
            lang_items = load_items(project_dir, config, lang_code)
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
        markdown_path.write_text(markdown_report(report), encoding="utf-8")
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


def _evaluation_payload(evaluation) -> dict:
    return {
        "name": evaluation.name,
        "value": evaluation.value,
        "comment": evaluation.comment,
    }
