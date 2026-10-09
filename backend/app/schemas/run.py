"""Run lifecycle contract. Mirrors contracts/run_status.schema.json."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .result import InstanceSummary, RunResult

RunStatusValue = Literal["queued", "running", "succeeded", "failed"]


class RunCreated(BaseModel):
    run_id: str
    status: RunStatusValue


class RunProgress(BaseModel):
    generation: int
    max_generations: int


class RunError(BaseModel):
    code: str
    message: str


class RunStatus(BaseModel):
    run_id: str
    status: RunStatusValue
    title: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress: RunProgress | None
    error: RunError | None
    result: RunResult | None


class RunSummary(BaseModel):
    run_id: str
    title: str | None
    status: RunStatusValue
    created_at: datetime
    task_count: int
    num_stations: int | None
    efficiency: float | None


class ValidateResponse(BaseModel):
    valid: bool
    instance: InstanceSummary
