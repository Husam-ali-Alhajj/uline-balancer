"""Descriptive metrics of a solution. Formulas are documented in MASTER.md section 5."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .types import EPS

HIGH_IDLE_FRACTION = 0.20  # a station is 'high idle' when idle > 20% of the cycle time


@dataclass(frozen=True)
class Metrics:
    efficiency: float
    balance_delay: float
    total_idle_time: float
    smoothness_index: float
    bottleneck_stations: list[int]
    high_idle_stations: list[int]
    idle_time_variation: float
    gap_to_minimum: float | None = None


def compute_metrics(
    cycle_time: float, loads: list[float], min_stations: int | None = None
) -> Metrics:
    """loads: total task time of each station, in station order.

    min_stations (N_min) is needed only for gap_to_minimum; without it the gap is None.
    """
    m = len(loads)
    total_work = sum(loads)
    capacity = m * cycle_time
    max_load = max(loads)
    efficiency = total_work / capacity
    smoothness = math.sqrt(sum((max_load - load) ** 2 for load in loads))
    idle = [cycle_time - load for load in loads]
    return Metrics(
        efficiency=round(efficiency, 4),
        balance_delay=round(1 - efficiency, 4),
        total_idle_time=round(capacity - total_work, 4),
        smoothness_index=round(smoothness, 4),
        bottleneck_stations=[i for i, load in enumerate(loads, 1) if load >= max_load - EPS],
        high_idle_stations=[
            i for i, value in enumerate(idle, 1) if value > HIGH_IDLE_FRACTION * cycle_time + EPS
        ],
        idle_time_variation=round(math.sqrt(sum(value**2 for value in idle) / m), 4),
        gap_to_minimum=None if min_stations is None else round((m - min_stations) / min_stations, 4),
    )
