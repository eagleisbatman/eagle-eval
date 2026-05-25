"""Process-isolated local item scoring with hard timeouts."""

from __future__ import annotations

import multiprocessing as mp
import queue
import time
from pathlib import Path

from eagle_eval.evaluation_types import Evaluation
from eagle_eval.local_item_scoring import evaluation_payload, failed_item, item_payload


def run_items_with_deadline(
    *,
    config: dict,
    project_dir: Path,
    lang_code: str,
    items: list[dict],
    prompt_versions: dict,
    include_model_scorers: bool,
    timeout_seconds: int,
    concurrency: int,
) -> list[tuple[dict, dict[str, float]]]:
    """Score items in child processes so stuck agents can be terminated."""
    if not items:
        return []
    ctx = mp.get_context("spawn")
    pending = iter(enumerate(items))
    ordered: list[tuple[dict, dict[str, float]] | None] = [None] * len(items)
    active: list[_ProcessJob] = []
    max_workers = max(1, int(concurrency or 1))

    while True:
        filled = _fill_active(
            active, pending, max_workers, ctx, config, project_dir,
            lang_code, prompt_versions, include_model_scorers,
        )
        if not active and not filled:
            break
        now = time.monotonic()
        still_active = []
        for job in active:
            result = _collect_job(job, now, timeout_seconds)
            if result is None:
                still_active.append(job)
            else:
                ordered[job.index] = result
        active = still_active
        if active:
            time.sleep(0.05)

    return [result for result in ordered if result is not None]


class _ProcessJob:
    def __init__(self, index: int, item: dict, process, result_queue, started_at: float):
        self.index = index
        self.item = item
        self.process = process
        self.result_queue = result_queue
        self.started_at = started_at


def _fill_active(active: list, pending, max_workers: int, ctx, config, project_dir, lang_code, prompt_versions, include_model_scorers) -> bool:
    filled = False
    while len(active) < max_workers:
        try:
            index, item = next(pending)
        except StopIteration:
            return filled
        result_queue = ctx.Queue(maxsize=1)
        process = ctx.Process(
            target=_worker,
            args=(result_queue, config, str(project_dir), lang_code, item, prompt_versions, include_model_scorers),
        )
        process.start()
        active.append(_ProcessJob(index, item, process, result_queue, time.monotonic()))
        filled = True
    return filled


def _collect_job(job: _ProcessJob, now: float, timeout_seconds: int):
    if job.process.is_alive() and now - job.started_at <= timeout_seconds:
        return None
    if job.process.is_alive():
        _terminate(job.process)
        return _timeout_item(job.item, timeout_seconds)

    job.process.join(timeout=0.2)
    try:
        status, payload = job.result_queue.get(timeout=0.2)
    except queue.Empty:
        return failed_item(
            "unknown",
            job.item,
            RuntimeError(f"Scoring process exited with code {job.process.exitcode}"),
        )
    if status == "ok":
        return payload
    return failed_item("unknown", job.item, RuntimeError(str(payload)))


def _terminate(process) -> None:
    process.terminate()
    process.join(timeout=1)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(timeout=1)


def _timeout_item(item: dict, timeout_seconds: int):
    comment = f"Exceeded item_timeout_seconds={timeout_seconds}"
    evaluation = Evaluation(name="item_timeout", value=0.0, comment=comment)
    output = {"responses": [], "tools_called": [], "metadata": {}, "error": comment}
    lang_code = item.get("metadata", {}).get("language", item.get("input", {}).get("language", "unknown"))
    return item_payload(lang_code, item, output, [evaluation_payload(evaluation)]), {"item_timeout": 0.0}


def _worker(result_queue, config: dict, project_dir: str, lang_code: str, item: dict, prompt_versions: dict, include_model_scorers: bool) -> None:
    try:
        from eagle_eval.agent_calling import load_agent
        from eagle_eval.custom_scoring import load_custom_evaluators
        from eagle_eval.evaluators import configure as configure_evaluators, get_item_evaluators
        from eagle_eval.imports import project_import_context
        from eagle_eval.local_item_scoring import safe_score_item

        root = Path(project_dir)
        with project_import_context(root, config["agent"]["module"]):
            custom_evaluators = load_custom_evaluators(config, root)
            configure_evaluators(
                scorer_model=config["scoring"]["scorer_model"],
                scorer=config["scoring"].get("scorer"),
                domain=config["domain"],
                app_context=config["app_context"],
                custom_evaluators=custom_evaluators,
            )
            evaluators = get_item_evaluators(include_model_scorers=include_model_scorers)
            result_queue.put(("ok", safe_score_item(lang_code, item, load_agent(config), prompt_versions, evaluators)))
    except BaseException as exc:
        result_queue.put(("error", str(exc)))
