"""Local result destination for running evals without a hosted service."""
from __future__ import annotations
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from eagle_eval.agent_calling import load_agent
from eagle_eval.file_io import atomic_write_json, atomic_write_text
from eagle_eval.local_item_scoring import safe_score_item
from eagle_eval.goal_summary import build_goal_summary
from eagle_eval.local_datasets import load_items, local_results_dir
from eagle_eval.local_reports import markdown_report
from eagle_eval.path_safety import safe_filename_part


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
        timeout_seconds = int(config["scoring"].get("item_timeout_seconds") or 0)
        results_dir = local_results_dir(config, project_dir)
        runs_dir = results_dir / "runs"

        agent_fn = evaluators = None
        if timeout_seconds <= 0:
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
            agent_fn = load_agent(config)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        pv_str = "-".join(f"{key}v{value}" for key, value in sorted(prompt_versions.items()))
        run_name = "-".join(
            safe_filename_part(part, "run")
            for part in [run_prefix, "local", pv_str, timestamp]
            if part
        )

        all_scores: dict[str, dict[str, float]] = {}
        item_results = []
        total_items = 0
        for lang_code in lang_codes:
            lang_items = load_items(project_dir, config, lang_code)
            total_items += len(lang_items)
            score_lists: dict[str, list[float]] = defaultdict(list)
            if timeout_seconds > 0:
                processed_items = _run_language_items_with_timeout(
                    config, project_dir, lang_code, lang_items, prompt_versions,
                    include_model_scorers, timeout_seconds, concurrency,
                )
            else:
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

        if total_items == 0:
            languages = ", ".join(lang_codes)
            raise RuntimeError(
                f"No eval items found for requested languages: {languages}. "
                "Run 'eagle-eval generate', review with 'eagle-eval gate', then "
                f"run 'eagle-eval upload --languages {languages}' for local datasets."
            )

        runs_dir.mkdir(parents=True, exist_ok=True)
        summary = build_goal_summary(item_results)
        report = {
            "run_name": run_name,
            "timestamp": timestamp,
            "destination": "local",
            "prompt_versions": prompt_versions,
            "scores": all_scores,
            "summary": summary,
            "items": item_results,
            "settings": {
                "include_model_scorers": include_model_scorers,
                "concurrency_requested": concurrency,
            },
        }
        json_path = runs_dir / f"{run_name}.json"
        markdown_path = runs_dir / f"{run_name}.md"
        atomic_write_json(json_path, report)
        atomic_write_text(markdown_path, markdown_report(report))
        return {
            "scores": all_scores,
            "prompt_versions": prompt_versions,
            "timestamp": timestamp,
            "summary": summary,
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
            safe_score_item(lang_code, item, agent_fn, prompt_versions, evaluators)
            for item in items
        ]

    ordered_results: list[tuple[dict, dict[str, float]] | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(safe_score_item, lang_code, item, agent_fn, prompt_versions, evaluators): index
            for index, item in enumerate(items)
        }
        for future in as_completed(futures):
            ordered_results[futures[future]] = future.result()

    return [result for result in ordered_results if result is not None]


def _run_language_items_with_timeout(
    config: dict,
    project_dir: Path,
    lang_code: str,
    items: list[dict],
    prompt_versions: dict,
    include_model_scorers: bool,
    timeout_seconds: int,
    concurrency: int,
) -> list[tuple[dict, dict[str, float]]]:
    from eagle_eval.local_process_scoring import run_items_with_deadline

    return run_items_with_deadline(
        config=config,
        project_dir=project_dir,
        lang_code=lang_code,
        items=items,
        prompt_versions=prompt_versions,
        include_model_scorers=include_model_scorers,
        timeout_seconds=timeout_seconds,
        concurrency=concurrency,
    )
