"""U-line placement rule and the independent feasibility checker.

U-line rule: a task may be placed when ALL its predecessors are already assigned
(it is then on the 'front' leg of the U) or ALL its successors are already
assigned (it is then on the 'back' leg).

Side labelling rule R2 (docs/DECISIONS.md; depends only on the precedence graph and
the stations, never on input order):
  1. 'front' if all predecessors are in earlier stations;
  2. else 'back' if all successors are in earlier stations;
  3. then, repeatedly, 'front' if all predecessors are in earlier stations or are
     'front' tasks of this station (front closure);
  4. every remaining task is 'back'.
Steps 1 and 2 follow the IE document's own reasons ("entry side, since A is assigned",
"exit side, since D is assigned"). Every labelling satisfies the IE unfolded-U
condition p_h <= p_i.

The station is then ordered: front tasks first (each after its predecessors), then
back tasks (each after its successors). A station is feasible if and only if this
places every task: placing a task only ever makes more tasks eligible, so one greedy
pass is a correct check, not a heuristic.
"""

from __future__ import annotations

from collections.abc import Iterable

from .types import EPS, Instance, Placement


def is_eligible(
    instance: Instance, name: str, done: set[str], succ: dict[str, tuple[str, ...]]
) -> str | None:
    """The U-line rule for one task: 'front' if all its predecessors are in `done`, else 'back'
    if all its successors are in `done`, else None. `succ` is instance.successors()."""
    if all(p in done for p in instance.predecessors[name]):
        return "front"
    if all(s in done for s in succ[name]):
        return "back"
    return None


def place_station(
    instance: Instance, station_tasks: Iterable[str], assigned: set[str]
) -> list[Placement] | None:
    """Order the tasks of one station. Returns None if the station is infeasible.

    `assigned` holds the tasks of all earlier stations. It is not modified.
    """
    wanted = set(station_tasks)
    tasks = [name for name in instance.order if name in wanted]
    succ = instance.successors()

    # steps 1 and 2: the side is decided by the earlier stations alone
    side = {}
    for name in tasks:
        label = is_eligible(instance, name, assigned, succ)
        if label is not None:
            side[name] = label

    # step 3: front closure inside the station; this is also the front tasks' order
    done = set(assigned)
    placed = [Placement(name, "front") for name in tasks if side.get(name) == "front"]
    done.update(p.name for p in placed)
    progressed = True
    while progressed:
        progressed = False
        for name in tasks:
            if name not in side and is_eligible(instance, name, done, succ) == "front":
                side[name] = "front"
                placed.append(Placement(name, "front"))
                done.add(name)
                progressed = True

    # step 4: the rest is back; each back task goes after all its successors
    backs = [name for name in tasks if side.get(name, "back") == "back"]
    while backs:
        ready = next((n for n in backs if all(s in done for s in succ[n])), None)
        if ready is None:
            return None
        placed.append(Placement(ready, "back"))
        done.add(ready)
        backs.remove(ready)
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
