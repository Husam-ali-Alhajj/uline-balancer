"""Shared helpers for the tests (plain Python, no pytest needed)."""

import json
from pathlib import Path

from app.ga.types import Instance

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def load_example(name: str) -> dict:
    return json.loads((CONTRACTS / "examples" / name).read_text())


def instance_from_input(data: dict) -> Instance:
    cycle = data["working_time_per_day"] / data["production_per_day"]
    return Instance(
        times={t["name"]: float(t["time"]) for t in data["tasks"]},
        predecessors={t["name"]: tuple(t.get("predecessors", [])) for t in data["tasks"]},
        cycle_time=cycle,
        order=tuple(t["name"] for t in data["tasks"]),
    )
