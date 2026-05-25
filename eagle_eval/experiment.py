"""Run experiments: replay conversations against the agent, score with evaluators."""

import importlib
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from eagle_eval.agent_calling import call_agent

log = logging.getLogger(__name__)


def run_experiment(config: dict, lang_codes: list[str], prompt_versions: dict,
                   concurrency: int, run_prefix: str = "", verbose: bool = False,
                   project_dir: Path | None = None) -> dict:
    """Run the agent against stored datasets and evaluate."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    destination = str(config.get("results", {}).get("destination", "langfuse")).strip().lower()
    project_dir = project_dir or Path.cwd()
    if destination == "local":
        from eagle_eval.local_results import run_local_experiment

        return run_local_experiment(
            config=config,
            lang_codes=lang_codes,
            prompt_versions=prompt_versions,
            concurrency=concurrency,
            project_dir=project_dir,
            run_prefix=run_prefix,
            verbose=verbose,
        )

    if destination != "langfuse":
        raise RuntimeError(
            f"Live experiment runs currently support Langfuse. Configured result destination: {destination}. "
            "Run 'eagle-eval doctor --verbose' to inspect SDK readiness."
        )

    try:
        from langfuse import get_client
    except ImportError as exc:
        raise RuntimeError(
            "The Langfuse result destination requires the Langfuse extra. "
            "Install it with: python -m pip install 'eagle-eval[langfuse]'"
        ) from exc
    from eagle_eval.custom_scoring import load_custom_evaluators
    from eagle_eval.evaluators import get_item_evaluators, configure as configure_evaluators
    from eagle_eval.imports import project_import_context

    lf = get_client()
    prefix = config.get("langfuse", {}).get("dataset_prefix", "evals")
    agent_module = config["agent"]["module"]
    agent_function = config["agent"]["function"]
    scorer = config["scoring"].get("scorer")
    scorer_model = config["scoring"]["scorer_model"]
    domain = config["domain"]
    timeout = config["scoring"].get("item_timeout_seconds", 120)

    with project_import_context(project_dir, agent_module):
        custom_evaluators = load_custom_evaluators(config, project_dir)
        configure_evaluators(
            scorer_model=scorer_model,
            scorer=scorer,
            domain=domain,
            app_context=config["app_context"],
            custom_evaluators=custom_evaluators,
        )

        # Import the agent
        try:
            mod = importlib.import_module(agent_module)
            agent_fn = getattr(mod, agent_function)
        except (ImportError, AttributeError) as e:
            raise RuntimeError(
                f"Cannot import agent: {agent_module}.{agent_function} — {e}\n"
                f"Make sure the agent module is importable from the current directory."
            ) from e

        # Fetch prompt objects from the result destination when supported.
        prompts = {}
        for prompt_name, version in prompt_versions.items():
            try:
                prompts[prompt_name] = lf.get_prompt(prompt_name, version=version)
                log.info(f"Fetched prompt '{prompt_name}' v{version}")
            except Exception as e:
                log.warning(f"Could not fetch prompt '{prompt_name}' v{version}: {e}")
                prompts[prompt_name] = None

        # Build the task function
        def task(*, item, **kwargs):
            return call_agent(agent_fn, item.input, prompt_versions)

        # Run per language
        all_scores = {}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        pv_str = "-".join(f"{k}v{v}" for k, v in sorted(prompt_versions.items()))

        for lang_code in lang_codes:
            dataset_name = f"{prefix}/{lang_code}/conversations"

            try:
                dataset = lf.get_dataset(dataset_name)
            except Exception as e:
                log.warning(f"Dataset '{dataset_name}' not found: {e}")
                continue

            run_name_parts = [run_prefix, lang_code, pv_str, timestamp]
            run_name = "-".join(p for p in run_name_parts if p)

            log.info(f"Running experiment: {run_name} on {dataset_name}")

            try:
                result = dataset.run_experiment(
                    name=run_name,
                    task=task,
                    evaluators=get_item_evaluators(),
                    # Note: run_evaluators support depends on the installed SDK version.
                    # If not supported, run-level aggregation happens in the compare script
                    max_concurrency=concurrency,
                    metadata={
                        "prompt_versions": prompt_versions,
                        "language": lang_code,
                        "agent": f"{agent_module}.{agent_function}",
                    },
                )

                # Extract scores from result
                lang_scores = _extract_scores(result)
                all_scores[lang_code] = lang_scores

                log.info(f"Completed {run_name}: {json.dumps(lang_scores)}")

            except Exception as e:
                log.error(f"Experiment failed for {lang_code}: {e}")
                all_scores[lang_code] = {"error": str(e)}

    lf.flush()

    return {"scores": all_scores, "prompt_versions": prompt_versions, "timestamp": timestamp}


def _extract_scores(result) -> dict:
    """Extract average scores from an experiment result object."""
    scores = {}

    # The result object's structure depends on the installed SDK version.
    # Try the format() approach first for display, then extract numerics
    try:
        if hasattr(result, "scores") and result.scores:
            for score_name, score_val in result.scores.items():
                if isinstance(score_val, (int, float)):
                    scores[score_name] = round(float(score_val), 3)
                elif hasattr(score_val, "mean"):
                    scores[score_name] = round(float(score_val.mean), 3)
    except Exception:
        pass

    # Fallback: try to get from individual item results
    if not scores:
        try:
            if hasattr(result, "experiment_items"):
                from collections import defaultdict
                score_lists = defaultdict(list)
                for item in result.experiment_items:
                    if hasattr(item, "evaluations"):
                        for ev in item.evaluations:
                            if ev.value is not None:
                                score_lists[ev.name].append(ev.value)
                for name, vals in score_lists.items():
                    scores[name] = round(sum(vals) / len(vals), 3)
        except Exception as e:
            log.warning(f"Could not extract item-level scores: {e}")

    return scores
