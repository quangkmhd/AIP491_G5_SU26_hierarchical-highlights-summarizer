from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


def parallel_map_ordered(
    items: Sequence[InputT],
    worker: Callable[[InputT], OutputT],
    *,
    max_workers: int | None = None,
) -> list[OutputT]:
    if not items:
        return []
    if len(items) == 1:
        return [worker(items[0])]

    worker_count = min(max_workers or len(items), len(items))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(worker, items))
