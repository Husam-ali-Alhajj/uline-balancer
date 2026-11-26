"""Run lifecycle: create, execute (in a worker process), read, list, delete."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, null, select, update
from sqlalchemy.orm import Session

from app.db.models import Run
from app.db.session import SessionLocal
from app.schemas.problem import ProblemInput
from app.schemas.result import RunResult
from app.schemas.run import RunError, RunProgress, RunStatus, RunSummary
from app.services.executor import get_executor
from app.services.solver import SolverError, solve_problem

logger = logging.getLogger(__name__)
ACTIVE = ("queued", "running")
_create_lock = threading.Lock()  # see create_run_within_cap


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes; they are always UTC here.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def create_run(session: Session, problem: ProblemInput) -> Run:
    run = Run(
        id=uuid.uuid4(),
        title=problem.title,
        status="queued",
        input=problem.model_dump(mode="json"),
        created_at=_now(),
    )
    session.add(run)
    session.commit()
    return run


def create_run_within_cap(session: Session, problem: ProblemInput, max_active: int) -> Run | None:
    """Create a run unless `max_active` runs are already queued or running (then return None).

    The lock makes the count and the insert one step, so concurrent requests cannot all pass the
    check. It is per process: the server must run as a single uvicorn process (backend/README.md).
    """
    with _create_lock:
        if count_active(session) >= max_active:
            return None
        return create_run(session, problem)


def start_run(run_id: str) -> None:
    get_executor().submit(execute_run, run_id)


def count_active(session: Session) -> int:
    stmt = select(func.count()).select_from(Run).where(Run.status.in_(ACTIVE))
    return session.execute(stmt).scalar_one()


def mark_stale_runs_failed() -> None:
    """On startup: a run left queued/running by a restart would hang forever."""
    with SessionLocal() as session:
        session.execute(
            update(Run)
            .where(Run.status.in_(ACTIVE))
            .values(
                status="failed",
                finished_at=_now(),
                error={"code": "server_restarted", "message": "The server restarted during this run."},
            )
        )
        session.commit()


def get_run(session: Session, run_id: str) -> Run | None:
    try:
        key = uuid.UUID(run_id)
    except ValueError:
        return None
    return session.get(Run, key)


def to_status(run: Run) -> RunStatus:
    progress = None
    if run.progress_generation is not None and run.progress_max:
        progress = RunProgress(generation=run.progress_generation, max_generations=run.progress_max)
    return RunStatus(
        run_id=str(run.id),
        status=run.status,
        title=run.title,
        created_at=_aware(run.created_at),
        started_at=_aware(run.started_at),
        finished_at=_aware(run.finished_at),
        progress=progress,
        error=RunError(**run.error) if run.error else None,
        result=RunResult.model_validate(run.result) if run.status == "succeeded" and run.result else None,
    )


def list_runs(session: Session, limit: int = 50) -> list[RunSummary]:
    runs = session.execute(select(Run).order_by(Run.created_at.desc()).limit(limit)).scalars()
    summaries = []
    for run in runs:
        result = run.result or {}
        summaries.append(
            RunSummary(
                run_id=str(run.id),
                title=run.title,
                status=run.status,
                created_at=_aware(run.created_at),
                task_count=len(run.input.get("tasks", [])),
                num_stations=result.get("solution", {}).get("num_stations"),
                efficiency=result.get("metrics", {}).get("efficiency"),
            )
        )
    return summaries


def delete_run(session: Session, run: Run) -> None:
    session.delete(run)
    session.commit()


# ---- worker side: runs in a separate process (or inline in tests) ----------------


def _update_if_status(run_id: uuid.UUID, expected: str, **values: object) -> bool:
    """Update the run only while it still has status `expected`. Returns False if it did not.

    A worker can outlive the server that started it; by then the restarted server has marked
    the run failed (server_restarted), and the worker must not overwrite that.
    """
    with SessionLocal() as session:
        outcome = session.execute(
            update(Run).where(Run.id == run_id, Run.status == expected).values(**values)
        )
        session.commit()
        return outcome.rowcount == 1


class _ProgressWriter:
    """Writes a run's latest progress from a background thread, at most once per `interval` seconds.

    The GA only records the latest generation and never waits for the database: on a remote
    database one write takes over a second, which used to slow the GA down by the same amount.
    """

    def __init__(self, run_id: uuid.UUID, interval: float = 1.0) -> None:
        self._run_id = run_id
        self._interval = interval
        self._lock = threading.Lock()
        self._latest: tuple[int, int] | None = None
        self._written: tuple[int, int] | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def update(self, generation: int, max_generations: int) -> None:
        with self._lock:
            self._latest = (generation, max_generations)

    def stop(self) -> dict:
        """Stop the thread and return the latest progress, to be written with the final status."""
        self._stop.set()
        self._thread.join()
        with self._lock:
            latest = self._latest
        if latest is None:
            return {}
        return {"progress_generation": latest[0], "progress_max": latest[1]}

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            with self._lock:
                latest = self._latest
            if latest is None or latest == self._written:
                continue
            try:
                _update_if_status(
                    self._run_id, "running", progress_generation=latest[0], progress_max=latest[1]
                )
                self._written = latest
            except Exception:  # a failed progress write must not stop the run; retried next tick
                logger.warning("progress write for run %s failed", self._run_id, exc_info=True)


def _fail(run_id: uuid.UUID, code: str, message: str, final_progress: dict) -> None:
    error = {"code": code, "message": message}
    if not _update_if_status(
        run_id, "running", status="failed", error=error, finished_at=_now(), **final_progress
    ):
        logger.warning("run %s is no longer running; discarding its error %s", run_id, code)


def execute_run(run_id: str) -> None:
    key = uuid.UUID(run_id)
    with SessionLocal() as session:
        run = session.get(Run, key)
        if run is None:
            return
        data = run.input
    if not _update_if_status(key, "queued", status="running", started_at=_now()):
        logger.warning("run %s is no longer queued; not starting it", run_id)
        return
    problem = ProblemInput.model_validate(data)

    writer = _ProgressWriter(key)
    writer.start()
    try:
        result = solve_problem(problem, writer.update)
    except SolverError as exc:
        _fail(key, exc.code, str(exc), writer.stop())
        return
    except Exception:
        logger.exception("run %s failed", run_id)
        _fail(key, "internal_error", "The run failed unexpectedly. Please try again.", writer.stop())
        return
    # the latest progress is written together with the final status
    final_progress = writer.stop()

    stored = _update_if_status(
        key,
        "running",
        status="succeeded",
        result=result.model_dump(mode="json"),
        model_version=result.model_version,
        error=null(),
        finished_at=_now(),
        **final_progress,
    )
    if not stored:
        logger.warning("run %s was marked failed while it ran; discarding its result", run_id)
