"""Import helpers for loading developer-owned agent modules."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator


@contextmanager
def project_import_context(project_dir: Path, module_name: str) -> Iterator[None]:
    """Temporarily prioritize a project path and clear stale module packages."""
    project_path = str(project_dir.expanduser().resolve())
    inserted = False
    if project_path not in sys.path:
        sys.path.insert(0, project_path)
        inserted = True

    _remove_stale_project_modules(module_name, project_path)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        importlib.invalidate_caches()
        if inserted:
            try:
                sys.path.remove(project_path)
            except ValueError:
                pass


def import_from_project(project_dir: Path, module_name: str) -> ModuleType:
    """Import a module with project_dir taking precedence for this import."""
    with project_import_context(project_dir, module_name):
        return importlib.import_module(module_name)


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
