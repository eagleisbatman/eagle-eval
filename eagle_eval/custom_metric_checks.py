"""Static validation for developer-owned custom scorer paths."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetricPath:
    module_name: str
    function_name: str


def split_metric_path(path: str) -> MetricPath:
    """Split a module:function custom metric path."""
    if ":" not in path:
        raise ValueError(f"Custom metric path must use module:function format: {path}")
    module_name, function_name = path.split(":", 1)
    if not module_name or not function_name:
        raise ValueError(f"Custom metric path must use module:function format: {path}")
    return MetricPath(module_name=module_name, function_name=function_name)


def check_metric_path(path: str, project_dir: Path) -> None:
    """Validate a custom metric path without importing project code."""
    metric_path = split_metric_path(path)
    module_file = resolve_module_file(project_dir, metric_path.module_name)
    tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
    if not _defines_callable(tree, metric_path.function_name):
        raise ValueError(
            f"Custom metric function '{metric_path.function_name}' was not found in {module_file}"
        )


def resolve_module_file(project_dir: Path, module_name: str) -> Path:
    """Resolve a dotted module name to a Python file under the eval project."""
    root = project_dir.expanduser().resolve()
    parts = module_name.split(".")
    module_path = (root / Path(*parts)).with_suffix(".py")
    package_path = root / Path(*parts) / "__init__.py"
    for path in (module_path, package_path):
        if _is_inside(path, root) and path.exists():
            return path
    raise FileNotFoundError(f"Custom metric module was not found: {module_name}")


def _defines_callable(tree: ast.Module, function_name: str) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return True
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == function_name for target in node.targets):
                return True
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == function_name:
                return True
    return False


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(root)
        return True
    except ValueError:
        return False
