"""Load developer-owned scoring functions from the eval workspace."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eagle_eval.custom_metric_checks import check_metric_path, split_metric_path
from eagle_eval.evaluation_types import Evaluation
from eagle_eval.imports import import_from_project


@dataclass(frozen=True)
class CustomMetricStatus:
    name: str
    path: str
    ok: bool
    error: str | None = None


def load_custom_evaluators(config: dict, project_dir: Path) -> list[Callable[..., Evaluation]]:
    """Load custom item evaluators declared in scoring.custom_metrics."""
    evaluators = []
    for metric in _custom_metrics(config):
        scorer_fn = _load_callable(metric["path"], project_dir)
        evaluators.append(_wrap_metric(metric, scorer_fn, config.get("app_context", {})))
    return evaluators


def load_custom_evaluator(config: dict, project_dir: Path, name: str) -> Callable[..., Evaluation]:
    """Load one custom item evaluator by metric name."""
    for metric in _custom_metrics(config):
        if metric["name"] == name:
            scorer_fn = _load_callable(metric["path"], project_dir)
            return _wrap_metric(metric, scorer_fn, config.get("app_context", {}))
    raise KeyError(f"Custom metric not found in scoring.custom_metrics: {name}")


def configured_custom_metrics(config: dict) -> list[dict]:
    """Return enabled and disabled custom metric declarations."""
    return list(config.get("scoring", {}).get("custom_metrics") or [])


def check_custom_metrics(config: dict, project_dir: Path) -> list[CustomMetricStatus]:
    """Return static readiness for custom metrics without executing project code."""
    statuses = []
    for metric in _custom_metrics(config):
        try:
            check_metric_path(metric["path"], project_dir)
            statuses.append(CustomMetricStatus(name=metric["name"], path=metric["path"], ok=True))
        except Exception as exc:
            statuses.append(
                CustomMetricStatus(name=metric["name"], path=metric["path"], ok=False, error=str(exc))
            )
    return statuses


def _custom_metrics(config: dict) -> list[dict]:
    metrics = config.get("scoring", {}).get("custom_metrics") or []
    return [metric for metric in metrics if metric.get("enabled", True)]


def _load_callable(path: str, project_dir: Path) -> Callable[..., Any]:
    metric_path = split_metric_path(path)
    module = import_from_project(project_dir, metric_path.module_name)
    scorer_fn = getattr(module, metric_path.function_name)
    if not callable(scorer_fn):
        raise TypeError(f"Custom metric is not callable: {path}")
    return scorer_fn


def _wrap_metric(metric: dict, scorer_fn: Callable[..., Any], app_context: dict) -> Callable[..., Evaluation]:
    metric_name = metric["name"]

    def evaluator(*, input, output, expected_output, metadata, **kwargs):
        result = _call_scorer(
            scorer_fn,
            {
                "input": input,
                "output": output,
                "expected_output": expected_output,
                "metadata": metadata,
                "context": app_context,
                "metric": metric,
            },
        )
        return _normalize_result(metric_name, result)

    evaluator.__name__ = metric_name
    return evaluator


def _call_scorer(scorer_fn: Callable[..., Any], kwargs: dict) -> Any:
    signature = inspect.signature(scorer_fn)
    accepts_kwargs = any(
        param.kind == inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    )
    if accepts_kwargs:
        return scorer_fn(**kwargs)

    supported = {
        name: value
        for name, value in kwargs.items()
        if name in signature.parameters
    }
    return scorer_fn(**supported)


def _normalize_result(metric_name: str, result: Any) -> Evaluation:
    if isinstance(result, Evaluation):
        return result

    if isinstance(result, bool):
        return Evaluation(name=metric_name, value=1.0 if result else 0.0, comment="")

    if isinstance(result, (int, float)):
        return Evaluation(name=metric_name, value=float(result), comment="")

    if isinstance(result, dict):
        name = result.get("name") or metric_name
        value = result.get("value", result.get("score"))
        if value is None:
            raise ValueError(f"Custom metric '{metric_name}' must return value or score")
        comment = result.get("comment") or result.get("reasoning") or ""
        details = result.get("details")
        if details:
            comment = f"{comment} details={details}" if comment else f"details={details}"
        return Evaluation(name=name, value=float(value), comment=str(comment))

    raise TypeError(
        f"Custom metric '{metric_name}' must return Evaluation, dict, bool, int, or float"
    )
