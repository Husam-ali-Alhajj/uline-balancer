"""U-line placement rule and the independent feasibility checker.

U-line rule: a task may be placed when ALL its predecessors are already assigned
(it is then on the 'front' leg of the U) or ALL its successors are already
assigned (it is then on the 'back' leg).

Side labelling rule (deterministic, so results are reproducible):
inside one station, repeat: place every task whose predecessors are all assigned
(side 'front', in input order); if none can be placed, place the first task whose
successors are all assigned (side 'back'). A task is therefore 'back' only when it
could not be placed as 'front'.

Placing a task only ever makes more tasks eligible, so a station is feasible if
and only if this loop places every task. That is why one greedy pass is a correct
check, not a heuristic.
"""

from __future__ import annotations

from collections.abc import Iterable

from .types import EPS, Instance, Placement


def place_station(
    instance: Instance, station_tasks: Iterable[str], assigned: set[str]
) -> list[Placement] | None:
    """Order the tasks of one station. Returns None if the station is infeasible.

    `assigned` holds the tasks of all earlier stations. It is not modified.
    """
    wanted = set(station_tasks)
    remaining = [name for name in instance.order if name in wanted]
    succ = instance.successors()
    done = set(assigned)
    placed: list[Placement] = []

    while remaining:
        progressed = False
        for name in list(remaining):
            if all(p in done for p in instance.predecessors[name]):
                placed.append(Placement(name, "front"))
                done.add(name)
                remaining.remove(name)
                progressed = True
        if progressed:
            continue
        for name in remaining:
            if all(s in done for s in succ[name]):
                placed.append(Placement(name, "back"))
                done.add(name)
                remaining.remove(name)
                progressed = True
                break
        if not progressed:
            return None
    return placed


def check_solution(instance: Instance, stations: list[list[str]]) -> list[str]:
    """Independent checker. Returns a list of problems; an empty list means valid.

    Use this in every GA test (requirement AI-N1: 100% feasible outputs).
    """
    problems: list[str] = []
    seen: dict[str, int] = {}
    for index, tasks in enumerate(stations, start=1):
        if not tasks:
            problems.append(f"station {index} is empty")
        for name in tasks:
            if name not in instance.times:
                problems.append(f"unknown task '{name}' in station {index}")
            elif name in seen:
                problems.append(f"task '{name}' appears in stations {seen[name]} and {index}")
            else:
                seen[name] = index
    for name in instance.order:
        if name not in seen:
            problems.append(f"task '{name}' is not assigned")
    if problems:
        return problems

    assigned: set[str] = set()
    for index, tasks in enumerate(stations, start=1):
        load = sum(instance.times[name] for name in tasks)
        if load > instance.cycle_time + EPS:
            problems.append(
                f"station {index} load {load:g} exceeds cycle time {instance.cycle_time:g}"
            )
        if place_station(instance, tasks, assigned) is None:
            problems.append(f"station {index} violates the U-line precedence rule")
        assigned.update(tasks)
    return problems
