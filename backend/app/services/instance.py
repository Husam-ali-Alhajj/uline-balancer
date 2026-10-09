"""Turns a validated ProblemInput into the plain types the GA uses."""

from __future__ import annotations

import math

from app.ga.types import Instance
from app.schemas.problem import ProblemInput
from app.schemas.result import InstanceSummary


def to_instance(problem: ProblemInput) -> Instance:
    return Instance(
        times={t.name: t.time for t in problem.tasks},
        predecessors={t.name: tuple(t.predecessors) for t in problem.tasks},
        cycle_time=problem.cycle_time,
        order=tuple(t.name for t in problem.tasks),
    )


def summarize(problem: ProblemInput) -> InstanceSummary:
    total = round(sum(t.time for t in problem.tasks), 4)
    cycle = problem.cycle_time
    return InstanceSummary(
        task_count=len(problem.tasks),
        total_work_content=total,
        cycle_time=round(cycle, 4),
        min_stations=max(1, math.ceil(total / cycle - 1e-9)),
    )
