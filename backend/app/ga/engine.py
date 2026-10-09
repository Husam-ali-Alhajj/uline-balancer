"""GA entry point.

WALKING SKELETON: this version does NOT run a genetic algorithm yet. It builds a
valid (but not optimised) solution by filling stations greedily in topological
order, so the whole system (API, database, frontend) can be tested end to end.
Replace the body of solve() with the real GA; keep the signature and the
SolveOutcome it returns.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from .fitness import compute_fitness
from .metrics import compute_metrics
from .placement import place_station
from .types import EPS, Instance, Placement, SolveOutcome

ProgressCallback = Callable[[int, int], None]


def _topological_order(instance: Instance) -> list[str]:
    indegree = {name: len(instance.predecessors[name]) for name in instance.order}
    succ = instance.successors()
    ready = [name for name in instance.order if indegree[name] == 0]
    result: list[str] = []
    while ready:
        name = ready.pop(0)
        result.append(name)
        for nxt in succ[name]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    return result


def solve(
    instance: Instance,
    settings: dict,
    seed: int | None = None,
    progress: ProgressCallback | None = None,
    time_limit_s: float = 60.0,
) -> SolveOutcome:
    started = time.perf_counter()
    used_seed = seed if seed is not None else random.randrange(2**31)
    max_generations = int(settings.get("max_generations", 100))
    if progress:
        progress(0, max_generations)

    groups: list[list[str]] = [[]]
    load = 0.0
    for name in _topological_order(instance):
        t = instance.times[name]
        if groups[-1] and load + t > instance.cycle_time + EPS:
            groups.append([])
            load = 0.0
        groups[-1].append(name)
        load += t

    stations: list[list[Placement]] = []
    assigned: set[str] = set()
    for group in groups:
        placed = place_station(instance, group, assigned)
        assert placed is not None  # forward greedy is always feasible
        stations.append(placed)
        assigned.update(group)

    loads = [sum(instance.times[p.name] for p in station) for station in stations]
    metrics = compute_metrics(instance.cycle_time, loads)
    fitness = compute_fitness(len(stations), metrics.smoothness_index, instance.cycle_time)
    return SolveOutcome(
        stations=stations,
        generations_run=0,
        stop_reason="max_generations",
        best_fitness=fitness,
        seed=used_seed,
        runtime_seconds=round(time.perf_counter() - started, 4),
        convergence=[(0, fitness, fitness)],
    )
