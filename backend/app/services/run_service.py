"""Run lifecycle: create, execute (in a worker process), read, list, delete."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes; they are always UTC here.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
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


def _fail(run_id: uuid.UUID, code: str, message: str) -> None:
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is not None:
            run.status = "failed"
            run.error = {"code": code, "message": message}
            run.finished_at = _now()
            session.commit()


def execute_run(run_id: str) -> None:
    key = uuid.UUID(run_id)
    with SessionLocal() as session:
        run = session.get(Run, key)
        if run is None:
            return
        run.status = "running"
        run.started_at = _now()
        session.commit()
        problem = ProblemInput.model_validate(run.input)

    last_write = 0.0

    def progress(generation: int, max_generations: int) -> None:
        nonlocal last_write
        now = time.monotonic()
        if now - last_write < 1.0 and generation < max_generations:
            return
        last_write = now
        with SessionLocal() as ps:
            row = ps.get(Run, key)
            if row is not None:
                row.progress_generation = generation
                row.progress_max = max_generations
                ps.commit()

    try:
        result = solve_problem(problem, progress)
    except SolverError as exc:
        _fail(key, exc.code, str(exc))
        return
    except Exception:
        logger.exception("run %s failed", run_id)
        _fail(key, "internal_error", "The run failed unexpectedly. Please try again.")
        return

    with SessionLocal() as session:
        run = session.get(Run, key)
        if run is not None:
            run.status = "succeeded"
            run.result = result.model_dump(mode="json")
            run.model_version = result.model_version
            run.finished_at = _now()
            session.commit()
