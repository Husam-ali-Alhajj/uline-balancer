"""The active-run cap holds under concurrent POST /runs (Sprint 1 check G4)."""

import threading
import time

from helpers import load_example

from app import config
from app.services import run_service


def test_cap_holds_under_concurrent_posts(client, monkeypatch):
    run_service.mark_stale_runs_failed()  # start from zero active runs
    monkeypatch.setattr(run_service, "start_run", lambda run_id: None)  # runs stay queued
    real_count = run_service.count_active

    def slow_count(session):
        # widen the window between the count and the insert, so a missing lock always shows
        count = real_count(session)
        time.sleep(0.05)
        return count

    monkeypatch.setattr(run_service, "count_active", slow_count)

    total = config.MAX_ACTIVE_RUNS + 2
    barrier = threading.Barrier(total)
    codes: list[int] = []

    def post():
        barrier.wait()
        codes.append(client.post("/runs", json=load_example("six_task_input.json")).status_code)

    threads = [threading.Thread(target=post) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        run_service.mark_stale_runs_failed()  # do not leave queued runs for later tests

    assert sorted(codes) == [202] * config.MAX_ACTIVE_RUNS + [429] * 2
