"""Where runs execute. The GA is CPU-bound, so it runs in a separate process."""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ProcessPoolExecutor

from app import config


class InlineExecutor:
    """Runs the job immediately in the same process (used by tests)."""

    def submit(self, fn, *args):  # noqa: ANN001, ANN002
        fn(*args)

    def shutdown(self, wait: bool = True) -> None:
        pass


_executor = None


def get_executor():  # noqa: ANN201
    global _executor
    if _executor is None:
        if config.RUN_EXECUTOR == "inline":
            _executor = InlineExecutor()
        else:
            # 'spawn' gives every worker a fresh interpreter, which avoids sharing
            # database connections across processes.
            _executor = ProcessPoolExecutor(
                max_workers=config.MAX_WORKER_PROCESSES,
                mp_context=multiprocessing.get_context("spawn"),
            )
    return _executor


def shutdown_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None
