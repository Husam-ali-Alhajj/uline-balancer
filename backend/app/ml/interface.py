"""The fixed interface between the backend and any recommender.

The rule-based recommender ships first. A trained model (AI engineer) must implement
the same interface so nothing else in the project changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RecommendationInput:
    cycle_time: float
    min_stations: int
    num_stations: int
    efficiency: float
    station_loads: list[float]
    task_times: dict[str, float]
    high_idle_stations: list[int]


@dataclass(frozen=True)
class Recommendation:
    code: str  # stable identifier, e.g. "HIGH_IDLE_STATION"
    severity: str  # "info" or "warning"
    station: int | None
    message: str  # human-readable text shown in the UI
    triggered_by: str  # the metric that caused it (requirement ML-N4)


class Recommender(Protocol):
    model_version: str

    def recommend(self, data: RecommendationInput) -> list[Recommendation]: ...
