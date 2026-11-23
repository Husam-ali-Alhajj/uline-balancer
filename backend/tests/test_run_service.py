"""Worker writes are guarded by the run's status, so a run marked failed stays failed (check G3)."""

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
