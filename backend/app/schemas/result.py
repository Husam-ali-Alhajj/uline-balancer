"""Output contract. Mirrors contracts/run_result.schema.json (keep them in sync)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class InstanceSummary(BaseModel):
    task_count: int
    total_work_content: float
    cycle_time: float
    min_stations: int


class StationTask(BaseModel):
    name: str
    time: float
    side: Literal["front", "back"]


class Station(BaseModel):
    index: int
    tasks: list[StationTask]
    load: float
    idle: float
    utilization: float


class Solution(BaseModel):
    num_stations: int
    stations: list[Station]


class WorkersInfo(BaseModel):
    count: int
    suggested: int
    workload_per_worker: float


class Metrics(BaseModel):
    efficiency: float
    balance_delay: float
    total_idle_time: float
    smoothness_index: float
    bottleneck_stations: list[int]
    high_idle_stations: list[int]
    workers: WorkersInfo
    idle_time_variation: float | None = None
    gap_to_minimum: float | None = None


class ConvergencePoint(BaseModel):
    generation: int
    best_fitness: float
    avg_fitness: float


class StoredGASettings(BaseModel):
    """The GA settings saved with a result. Loose on purpose: a saved result is shown as it was saved and is
    never re-checked against today's limits, which live in problem.GASettings and apply to new requests only.
    Types only, no ranges or cross-field checks; a setting missing from an old result is None, and a setting
    that no longer exists is kept as saved."""

    model_config = ConfigDict(extra="allow")

    population_size: int | None = None
    max_generations: int | None = None
    crossover_rate: float | None = None
    mutation_rate: float | None = None
    elitism_count: int | None = None
    tournament_size: int | None = None
    stagnation_limit: int | None = None
    seed: int | None = None


class GARunInfo(BaseModel):
    seed: int
    settings: StoredGASettings
    generations_run: int
    stop_reason: Literal["max_generations", "stagnation", "time_limit"]
    best_fitness: float
    runtime_seconds: float
    convergence: list[ConvergencePoint]


class BaselineInfo(BaseModel):
    name: str
    num_stations: int
    efficiency: float


class Recommendation(BaseModel):
    code: str
    severity: Literal["info", "warning"]
    station: int | None
    message: str
    triggered_by: str


class RunResult(BaseModel):
    instance: InstanceSummary
    solution: Solution
    metrics: Metrics
    ga: GARunInfo
    baseline: BaselineInfo | None
    recommendations: list[Recommendation]
    model_version: str
