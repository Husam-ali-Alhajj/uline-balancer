from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import config
from app.api.errors import ApiError
from app.db.session import get_session
from app.schemas.problem import ProblemInput
from app.schemas.run import RunCreated, RunStatus, RunSummary
from app.services import run_service

router = APIRouter(prefix="/runs", tags=["runs"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", status_code=202, response_model=RunCreated)
def create_run(problem: ProblemInput, session: SessionDep) -> RunCreated:
    """Validate, create a run (status 'queued'), start it in the background, return its id."""
    if run_service.count_active(session) >= config.MAX_ACTIVE_RUNS:
        raise ApiError(429, "too_many_active_runs", "Too many runs in progress. Try again shortly.")
    run = run_service.create_run(session, problem)
    run_service.start_run(str(run.id))
    session.refresh(run)  # with the inline test executor the run may already be finished
    return RunCreated(run_id=str(run.id), status=run.status)


@router.get("", response_model=list[RunSummary])
def list_runs(session: SessionDep) -> list[RunSummary]:
    return run_service.list_runs(session)


@router.get("/{run_id}", response_model=RunStatus)
def get_run(run_id: str, session: SessionDep) -> RunStatus:
    run = run_service.get_run(session, run_id)
    if run is None:
        raise ApiError(404, "not_found", "Run not found.")
    return run_service.to_status(run)


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, session: SessionDep) -> Response:
    run = run_service.get_run(session, run_id)
    if run is None:
        raise ApiError(404, "not_found", "Run not found.")
    if run.status in run_service.ACTIVE:
        raise ApiError(409, "run_in_progress", "A run in progress cannot be deleted.")
    run_service.delete_run(session, run)
    return Response(status_code=204)
