"""Rule-based recommender (the always-available fallback, requirement ML-F2)."""

from __future__ import annotations

from .interface import Recommendation, RecommendationInput

LONG_TASK_FRACTION = 0.80
WELL_BALANCED_EFFICIENCY = 0.90


def _g(value: float) -> str:
    return f"{value:g}"


class RuleBasedRecommender:
    model_version = "rule-based-v0"

    def recommend(self, data: RecommendationInput) -> list[Recommendation]:
        out: list[Recommendation] = []
        n, m, c = data.num_stations, data.min_stations, data.cycle_time

        if n == m:
            out.append(
                Recommendation(
                    "MIN_STATIONS_REACHED",
                    "info",
                    None,
                    f"The solution uses {n} stations, the theoretical minimum for this cycle time.",
                    f"num_stations={n}, min_stations={m}",
                )
            )
        else:
            extra = n - m
            out.append(
                Recommendation(
                    "ABOVE_MIN_STATIONS",
                    "info",
                    None,
                    f"The solution uses {extra} more station(s) than the theoretical minimum of {m}; "
                    "precedence constraints or task sizes may prevent a better balance.",
                    f"num_stations={n}, min_stations={m}",
                )
            )

        for k in data.high_idle_stations:
            idle = c - data.station_loads[k - 1]
            pct = 100 * idle / c
            out.append(
                Recommendation(
                    "HIGH_IDLE_STATION",
                    "warning",
                    k,
                    f"Station {k} is idle {pct:.1f}% of the cycle time; consider moving work "
                    "to it or merging it with a neighbouring station.",
                    f"idle={_g(round(idle, 4))} min ({pct:.1f}% of cycle time)",
                )
            )

        for name, t in data.task_times.items():
            if t > LONG_TASK_FRACTION * c:
                out.append(
                    Recommendation(
                        "LONG_TASK",
                        "warning",
                        None,
                        f"Task {name} takes {100 * t / c:.0f}% of the cycle time and limits how "
                        "well the line can be balanced; consider splitting it.",
                        f"time={_g(t)} min, cycle_time={_g(c)} min",
                    )
                )

        if data.efficiency >= WELL_BALANCED_EFFICIENCY:
            out.append(
                Recommendation(
                    "WELL_BALANCED",
                    "info",
                    None,
                    f"Line efficiency is {100 * data.efficiency:.1f}%, which is well balanced.",
                    f"efficiency={data.efficiency:.4f}",
                )
            )
        return out
