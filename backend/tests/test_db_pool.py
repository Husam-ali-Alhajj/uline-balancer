"""Pool sizes per process (A.2.5): the server and each GA worker stay under the pooler limit."""

import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _pool_sizes() -> tuple[int, int]:
    from app.db.session import engine

    return engine.pool.size(), engine.pool._max_overflow


def test_server_process_uses_the_server_pool():
    code = ("import json, sys; sys.path.insert(0, '.'); from app.db.session import engine; "
            "print(json.dumps([engine.pool.size(), engine.pool._max_overflow]))")
    env = dict(os.environ, DB_POOL_SIZE="4", DB_MAX_OVERFLOW="1")
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == [4, 1]


def test_ga_worker_uses_the_worker_pool(monkeypatch):
    from app import config
    from app.services import executor

    monkeypatch.setenv("DB_WORKER_POOL_SIZE", "2")
    monkeypatch.setenv("DB_WORKER_MAX_OVERFLOW", "0")
    monkeypatch.setattr(config, "RUN_EXECUTOR", "process")
    executor.shutdown_executor()
    try:
        assert executor.get_executor().submit(_pool_sizes).result(timeout=120) == (2, 0)
    finally:
        executor.shutdown_executor()


def test_a_plain_spawned_process_uses_the_server_pool():
    """uvicorn --reload runs the server in a spawned child; it must still get the server pool."""
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as pool:
        assert pool.submit(_pool_sizes).result(timeout=120) == (3, 2)
