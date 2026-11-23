"""Shared helpers for the tests (plain Python, no pytest needed)."""

import json
from pathlib import Path

from app.ga.types import Instance

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def load_example(name: str) -> dict:
    return json.loads((CONTRACTS / "examples" / name).read_text())


def instance_from_input(data: dict) -> Instance:
    # MASTER.md section 5: C = (working time - break time) / production
    available = data["working_time_per_day"] - data.get("break_time_per_day", 0)
    cycle = available / data["production_per_day"]
    return Instance(
        times={t["name"]: float(t["time"]) for t in data["tasks"]},
        predecessors={t["name"]: tuple(t.get("predecessors", [])) for t in data["tasks"]},
        cycle_time=cycle,
        order=tuple(t["name"] for t in data["tasks"]),
    )


def random_instance(rng, n: int, p: float, cycle: int) -> Instance:
    """Random valid instance: n tasks, each earlier task is a predecessor with probability p,
    times 1..cycle, input order shuffled so it differs from the topological order."""
    names = [f"T{i}" for i in range(n)]
    predecessors = {x: tuple(q for q in names[:i] if rng.random() < p) for i, x in enumerate(names)}
    times = {x: float(rng.randint(1, cycle)) for x in names}
    order = names[:]
    rng.shuffle(order)
    return Instance(times=times, predecessors=predecessors, cycle_time=float(cycle), order=tuple(order))


def make_instance(spec, cycle: float) -> Instance:
    """spec: list of (name, time, predecessors)."""
    return Instance(
        times={n: float(t) for n, t, _ in spec},
        predecessors={n: tuple(p) for n, _, p in spec},
        cycle_time=float(cycle),
        order=tuple(n for n, _, _ in spec),
    )
