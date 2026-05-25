"""Small ordered concurrency helpers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def run_ordered(items: Iterable[T], max_concurrency: int, worker: Callable[[T], R]) -> list[R]:
    """Run jobs with bounded concurrency while preserving input order."""
    item_list = list(items)
    max_workers = max(1, int(max_concurrency or 1))
    if max_workers == 1 or len(item_list) <= 1:
        return [worker(item) for item in item_list]

    results: list[R | None] = [None] * len(item_list)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, item): index for index, item in enumerate(item_list)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [result for result in results if result is not None]
