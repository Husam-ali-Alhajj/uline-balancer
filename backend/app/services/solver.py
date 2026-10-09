"""Runs the GA and the recommender and assembles a RunResult. No database here."""

from __future__ import annotations

from collections.abc import Callable

from app import config
from app.ga import engine
from app.ga.metrics import compute_metrics
from app.ga.placement import check_solution
from app.ml.interface import RecommendationInput
from app.ml.registry import get_recommender
from app.ml.rule_based import RuleBasedRecommender
from app.schemas import result as r
from app.schemas.problem import ProblemInput
from app.services.instance import summarize, to_instance


class SolverError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def solve_problem(
    problem: ProblemInput, progress: Callable[[int, int], None] | None = None
) -> r.RunResult:
    instance = to_instance(problem)
    summary = summarize(problem)
    settings = problem.ga_settings.model_dump()
    outcome = engine.solve(
        instance,
        settings,
        seed=settings["seed"],
        progress=progress,
        time_limit_s=config.MAX_RUN_SECONDS,
    )

    names = [[p.name for p in station] for station in outcome.stations]
    problems = check_solution(instance, names)
    if problems:  # safety net: never return an infeasible solution (requirement AI-N1)
        raise SolverError("invalid_solution", "The solver produced an invalid solution.")

    cycle = instance.cycle_time
    stations: list[r.Station] = []
    loads: list[float] = []
    for index, placed in enumerate(outcome.stations, start=1):
        load = sum(instance.times[p.name] for p in placed)
        loads.append(load)
        stations.append(
            r.Station(
                index=index,
                tasks=[
                    r.StationTask(name=p.name, time=instance.times[p.name], side=p.side)
                    for p in placed
                ],
                load=round(load, 4),
                idle=round(cycle - load, 4),
                utilization=round(load / cycle, 4),
            )
        )

    m = len(stations)
    metrics = compute_metrics(cycle, loads)
    total = summary.total_work_content
    workers_count = problem.workers or m

    rec_input = RecommendationInput(
        cycle_time=cycle,
        min_stations=summary.min_stations,
        num_stations=m,
        efficiency=metrics.efficiency,
        station_loads=loads,
        task_times=dict(instance.times),
        high_idle_stations=metrics.high_idle_stations,
    )
    try:
        recommender = get_recommender()
        recs = recommender.recommend(rec_input)
        version = recommender.model_version
    except Exception:  # ML-N3: a recommender failure never blocks the result
        fallback = RuleBasedRecommender()
        recs = fallback.recommend(rec_input)
        version = fallback.model_version

    return r.RunResult(
        instance=summary,
        solution=r.Solution(num_stations=m, stations=stations),
        metrics=r.Metrics(
            efficiency=metrics.efficiency,
            balance_delay=metrics.balance_delay,
            total_idle_time=metrics.total_idle_time,
            smoothness_index=metrics.smoothness_index,
            bottleneck_stations=metrics.bottleneck_stations,
            high_idle_stations=metrics.high_idle_stations,
            workers=r.WorkersInfo(
                count=workers_count,
                suggested=m,
                workload_per_worker=round(total / workers_count, 4),
            ),
        ),
        ga=r.GARunInfo(
            seed=outcome.seed,
            settings=problem.ga_settings.model_copy(update={"seed": outcome.seed}),
            generations_run=outcome.generations_run,
            stop_reason=outcome.stop_reason,
            best_fitness=outcome.best_fitness,
            runtime_seconds=outcome.runtime_seconds,
            convergence=[
                r.ConvergencePoint(generation=g, best_fitness=b, avg_fitness=a)
                for g, b, a in outcome.convergence
            ],
        ),
        baseline=None,
        recommendations=[
            r.Recommendation(
                code=x.code,
                severity=x.severity,
                station=x.station,
                message=x.message,
                triggered_by=x.triggered_by,
            )
            for x in recs
        ],
        model_version=version,
    )
