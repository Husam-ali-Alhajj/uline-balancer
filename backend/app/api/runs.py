from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import config
from app.api.errors import ApiError
from app.auth import UserDep
from app.db.session import get_session
from app.schemas.problem import ProblemInput
from app.schemas.run import RunCreated, RunStatus, RunSummary
from app.services import run_service

router = APIRouter(prefix="/runs", tags=["runs"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", status_code=202, response_model=RunCreated)
def create_run(problem: ProblemInput, session: SessionDep, user: UserDep) -> RunCreated:
    """Validate, create a run (status 'queued'), start it in the background, return its id."""
    run = run_service.create_run_within_cap(session, problem, config.MAX_ACTIVE_RUNS, user)
    if run is None:
        raise ApiError(429, "too_many_active_runs", "Too many runs in progress. Try again shortly.")
    run_service.start_run(str(run.id))
    session.refresh(run)  # with the inline test executor the run may already be finished
    return RunCreated(run_id=str(run.id), status=run.status)


@router.get("", response_model=list[RunSummary])
def list_runs(session: SessionDep, user: UserDep) -> list[RunSummary]:
    return run_service.list_runs(session, user)


@router.get("/{run_id}", response_model=RunStatus)
def get_run(run_id: str, session: SessionDep, user: UserDep) -> RunStatus:
    run = run_service.get_visible_run(session, run_id, user)
    if run is None:
        raise ApiError(404, "not_found", "Run not found.")
    return run_service.to_status(run)


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, session: SessionDep, user: UserDep) -> Response:
    run = run_service.get_visible_run(session, run_id, user)
    if run is None or not run_service.can_delete(run, user):
        raise ApiError(404, "not_found", "Run not found.")
    if run.status in run_service.ACTIVE:
        raise ApiError(409, "run_in_progress", "A run in progress cannot be deleted.")
    run_service.delete_run(session, run)
    return Response(status_code=204)
