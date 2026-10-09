"""Fitness function (lower is better). PROVISIONAL: decision D7 is still open.

Primary goal: fewer stations. Tie-breaker: smoother workload. The tie-breaker term
is always below 1, so it can never outweigh one whole station.
"""

from __future__ import annotations


def compute_fitness(num_stations: int, smoothness_index: float, cycle_time: float) -> float:
    return round(num_stations + smoothness_index / (num_stations * cycle_time), 4)
