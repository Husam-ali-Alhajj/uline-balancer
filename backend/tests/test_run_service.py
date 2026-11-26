"""Worker writes are guarded by the run's status, so a run marked failed stays failed (check G3)."""

import time

from helpers import load_example

from app.db.session import SessionLocal
from app.schemas.problem import ProblemInput
from app.services import run_service
from app.services.solver import solve_problem


def _new_run() -> str:
    with SessionLocal() as session:
        run = run_service.create_run(session, ProblemInput.model_validate(load_example("six_task_input.json")))
        return str(run.id)


def _load(run_id: str):
    with SessionLocal() as session:
        return run_service.get_run(session, run_id)


def test_run_marked_failed_while_running_stays_failed(client, monkeypatch):
    run_id = _new_run()

    def restart_during_solve(problem, progress=None):
        result = solve_problem(problem)
        run_service.mark_stale_runs_failed()  # what a restarted server does
        progress(10, 10)  # a late progress write from the old worker
        return result

    monkeypatch.setattr(run_service, "solve_problem", restart_during_solve)
    run_service.execute_run(run_id)

    run = _load(run_id)
    assert run.status == "failed"
    assert run.error["code"] == "server_restarted"
    assert run.result is None
    assert run.progress_generation != 10


def test_run_already_failed_is_not_started(client):
    run_id = _new_run()
    run_service.mark_stale_runs_failed()
    run_service.execute_run(run_id)
    run = _load(run_id)
    assert run.status == "failed"
    assert run.started_at is None
    assert run.error["code"] == "server_restarted"


def test_successful_run_has_no_error(client):
    run_id = _new_run()
    run_service.execute_run(run_id)
    run = _load(run_id)
    assert run.status == "succeeded"
    assert run.error is None
    assert run.result is not None


def test_stagnation_stopped_run_reports_its_final_generation(client):
    data = load_example("six_task_input.json")
    data["ga_settings"].update(max_generations=1000, stagnation_limit=5)
    with SessionLocal() as session:
        run_id = str(run_service.create_run(session, ProblemInput.model_validate(data)).id)
    run_service.execute_run(run_id)
    run = _load(run_id)
    assert run.status == "succeeded"
    assert run.result["ga"]["stop_reason"] == "stagnation"
    assert run.progress_generation == run.result["ga"]["generations_run"] < 1000
    assert run.progress_max == 1000


def test_slow_progress_writes_do_not_slow_the_ga(client, monkeypatch):
    """On a remote database one write takes about a second; the GA must not wait for it."""
    original = run_service._update_if_status

    def slow_progress_write(run_id, expected, **values):
        if set(values) == {"progress_generation", "progress_max"}:
            time.sleep(0.5)
        return original(run_id, expected, **values)

    monkeypatch.setattr(run_service, "_update_if_status", slow_progress_write)
    run_id = _new_run()
    run_service.execute_run(run_id)
    run = _load(run_id)
    assert run.status == "succeeded"
    assert run.result["ga"]["runtime_seconds"] < 0.4
    assert run.progress_generation == run.result["ga"]["generations_run"]


def test_progress_is_written_while_the_run_is_running(client, monkeypatch):
    seen = []

    def solve_and_watch(problem, progress=None):
        progress(5, 100)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not seen:
            run = _load(run_id)
            if run.progress_generation == 5:
                seen.append((run.status, run.progress_generation, run.progress_max))
            time.sleep(0.05)
        return solve_problem(problem)

    monkeypatch.setattr(run_service, "solve_problem", solve_and_watch)
    run_id = _new_run()
    run_service.execute_run(run_id)
    assert seen == [("running", 5, 100)]
    assert _load(run_id).status == "succeeded"
