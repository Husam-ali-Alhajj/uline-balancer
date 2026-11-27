"""Exact solvers for Type 1 U-line balancing (minimum number of stations). Used to measure GA quality.

solve_exact: branch-and-bound for small instances (up to about 12 tasks). Stations are opened one at a
time. A station is any set of unassigned tasks that fits in the cycle time and can be added one by one
under the U-line rule (is_eligible in placement.py). Two facts keep the search small and still exact:
  - Only maximal stations (no further eligible task fits) are tried. Assigning more tasks never makes
    the rest harder: removing assigned tasks from a later solution keeps it feasible, because a task
    that is eligible stays eligible when more tasks are done.
  - Bound: stations used + ceil(remaining work / C) must be below the best solution found so far.
A node or time limit stops the search; the result is then "unknown" (with the best solution found).

solve_chain: exact dynamic programming for a pure chain T1 -> T2 -> ... -> Tn. Under the U-line rule
the unassigned tasks are always one contiguous run Ti..Tj, and a station takes some tasks from its
front end and some from its back end. DP over (front index, back index) is therefore exact.

Every returned solution is checked with check_solution.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from functools import cache

from .decoder import decode
from .placement import check_solution, is_eligible, place_station
from .types import EPS, Instance

NODE_LIMIT = 200_000


@dataclass(frozen=True)
class ExactResult:
    status: str  # "optimal" | "unknown" (limit hit: num_stations is only the best found)
    num_stations: int
    stations: list[list[str]]
    nodes: int = 0


def _min_stations(work: float, cycle_time: float) -> int:
    return max(0, math.ceil(work / cycle_time - EPS))


def _checked(instance: Instance, stations: list[list[str]]) -> list[list[str]]:
    ordered: list[list[str]] = []
    assigned: set[str] = set()
    for group in stations:
        placed = place_station(instance, group, assigned)
        if placed is None:
            raise AssertionError("exact solver built a station that violates the U-line rule")
        ordered.append([p.name for p in placed])
        assigned.update(group)
    problems = check_solution(instance, ordered)
    if problems:
        raise AssertionError(f"exact solver returned an invalid solution: {problems}")
    return ordered


def _maximal_stations(instance, succ, assigned: frozenset[str]) -> list[frozenset[str]]:
    """All maximal stations that can be opened after `assigned`, heaviest first."""
    free = [name for name in instance.order if name not in assigned]
    seen: set[frozenset[str]] = set()
    maximal: list[frozenset[str]] = []
    stack: list[tuple[frozenset[str], float]] = [(frozenset(), 0.0)]
    while stack:
        station, load = stack.pop()
        done = assigned | station
        extended = False
        for name in free:
            if name in station or load + instance.times[name] > instance.cycle_time + EPS:
                continue
            if is_eligible(instance, name, done, succ) is None:
                continue
            extended = True
            bigger = station | {name}
            if bigger not in seen:
                seen.add(bigger)
                stack.append((bigger, load + instance.times[name]))
        if not extended and station:
            maximal.append(station)
    position = {name: i for i, name in enumerate(instance.order)}
    load_of = {s: sum(instance.times[n] for n in s) for s in maximal}
    maximal.sort(key=lambda s: (-load_of[s], sorted(position[n] for n in s)))
    return maximal


def solve_exact(
    instance: Instance, node_limit: int = NODE_LIMIT, time_limit_s: float = 30.0
) -> ExactResult:
    started = time.perf_counter()
    succ = instance.successors()
    total = sum(instance.times.values())
    lower = _min_stations(total, instance.cycle_time)

    best = decode(instance, instance.order)  # a feasible start: the decoder on the input order
    best_stations = [list(s) for s in best]
    nodes = 0
    limit_hit = False
    reached: dict[frozenset[str], int] = {}  # fewest stations seen for each assigned set

    def search(assigned: frozenset[str], work_left: float, path: list[frozenset[str]]) -> None:
        nonlocal best_stations, nodes, limit_hit
        if len(assigned) == len(instance.order):
            if len(path) < len(best_stations):
                best_stations = [list(s) for s in path]
            return
        if len(path) + _min_stations(work_left, instance.cycle_time) >= len(best_stations):
            return
        if reached.get(assigned, math.inf) <= len(path):
            return
        reached[assigned] = len(path)
        for station in _maximal_stations(instance, succ, assigned):
            nodes += 1
            if nodes > node_limit or time.perf_counter() - started > time_limit_s:
                limit_hit = True
                return
            load = sum(instance.times[n] for n in station)
            path.append(station)
            search(assigned | station, work_left - load, path)
            path.pop()
            if limit_hit or len(best_stations) == lower:
                return

    search(frozenset(), total, [])
    if len(best_stations) == lower:
        limit_hit = False  # the lower bound proves the best solution optimal
    stations = _checked(instance, best_stations)
    return ExactResult("unknown" if limit_hit else "optimal", len(stations), stations, nodes)


def chain_order(instance: Instance) -> list[str] | None:
    """The tasks from first to last if the precedence graph is one chain, else None."""
    succ = instance.successors()
    heads = [n for n in instance.order if not instance.predecessors[n]]
    if len(heads) != 1:
        return None
    if any(len(instance.predecessors[n]) > 1 or len(succ[n]) > 1 for n in instance.order):
        return None
    chain = [heads[0]]
    while succ[chain[-1]]:
        chain.append(succ[chain[-1]][0])
    return chain if len(chain) == len(instance.order) else None


def solve_chain(instance: Instance) -> ExactResult:
    chain = chain_order(instance)
    if chain is None:
        raise ValueError("solve_chain needs a pure chain")
    n, cycle = len(chain), instance.cycle_time
    prefix = [0.0]
    for name in chain:
        prefix.append(prefix[-1] + instance.times[name])

    def load(i: int, j: int) -> float:  # tasks chain[i:j]
        return prefix[j] - prefix[i]

    @cache
    def best(i: int, j: int) -> tuple[int, int, int]:
        """Fewest stations for chain[i:j], with the first station's front and back counts."""
        if i == j:
            return 0, 0, 0
        result = (math.inf, 0, 0)
        a = 0
        while i + a <= j and load(i, i + a) <= cycle + EPS:
            # take a tasks from the front and as many as fit from the back (more never hurts)
            b = 0
            while i + a + b < j and load(i, i + a) + load(j - b - 1, j) <= cycle + EPS:
                b += 1
            if a + b:
                count = 1 + best(i + a, j - b)[0]
                if count < result[0]:
                    result = (count, a, b)
            a += 1
        return result

    stations: list[list[str]] = []
    i, j = 0, n
    while i < j:
        _, a, b = best(i, j)
        stations.append(chain[i : i + a] + chain[j - b : j])
        i, j = i + a, j - b
    stations = _checked(instance, stations)
    return ExactResult("optimal", len(stations), stations)
