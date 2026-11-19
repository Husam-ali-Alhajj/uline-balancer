"""Decoder: turns a chromosome (a permutation of task names) into stations.

Rule (docs/GA_DESIGN.md section 2, IE formulas document sections 5 and 9): open a station, then
repeatedly add the first unassigned task in chromosome order that is eligible (all predecessors or
all successors already assigned, counting the current station) and fits in the remaining time.
Close the station when no eligible task fits, and open the next one.

Every decoded solution is feasible by construction; place_station orders each station and is the
only place where the U-line rule is applied to a finished station.
"""

from __future__ import annotations

from collections.abc import Sequence

from .placement import place_station
from .types import EPS, Instance


def decode(instance: Instance, chromosome: Sequence[str]) -> list[list[str]]:
    """Return the stations as lists of task names, each in place_station order."""
    if len(chromosome) != len(instance.order) or set(chromosome) != set(instance.order):
        raise ValueError("chromosome must be a permutation of all task names")

    succ = instance.successors()
    assigned: set[str] = set()
    stations: list[list[str]] = []

    while len(assigned) < len(chromosome):
        before = set(assigned)
        group: list[str] = []
        remaining = instance.cycle_time
        added = True
        while added:
            added = False
            for name in chromosome:
                if name in assigned or instance.times[name] > remaining + EPS:
                    continue
                if all(p in assigned for p in instance.predecessors[name]) or all(
                    s in assigned for s in succ[name]
                ):
                    group.append(name)
                    assigned.add(name)
                    remaining -= instance.times[name]
                    added = True
                    break
        if not group:
            # cannot happen for a validated instance (every task time <= cycle time)
            raise ValueError("a task does not fit in an empty station")
        placed = place_station(instance, group, before)
        if placed is None:
            raise AssertionError("decoder built a station that violates the U-line rule")
        stations.append([p.name for p in placed])
    return stations
