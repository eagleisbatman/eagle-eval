"""Load developer-owned scoring functions from the eval workspace."""

from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eagle_eval.evaluators import Evaluation


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
    """Return import readiness for custom metrics without raising."""
    statuses = []
    for metric in _custom_metrics(config):
        try:
            _load_callable(metric["path"], project_dir)
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
    if ":" not in path:
        raise ValueError(f"Custom metric path must use module:function format: {path}")

    module_name, function_name = path.split(":", 1)
    project_path = str(project_dir.expanduser().resolve())
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    importlib.invalidate_caches()
    _remove_stale_project_modules(module_name, project_path)
    module = importlib.import_module(module_name)
    scorer_fn = getattr(module, function_name)
    if not callable(scorer_fn):
        raise TypeError(f"Custom metric is not callable: {path}")
    return scorer_fn


def _remove_stale_project_modules(module_name: str, project_path: str) -> None:
    package_name = module_name.split(".", 1)[0]
    package = sys.modules.get(package_name)
    if package is None:
        return

    package_paths = [str(Path(path).resolve()) for path in getattr(package, "__path__", [])]
    if any(path.startswith(project_path) for path in package_paths):
        return

    for loaded_name in list(sys.modules):
        if loaded_name == package_name or loaded_name.startswith(f"{package_name}."):
            del sys.modules[loaded_name]


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
