"""Plain data types shared by the GA, the metrics and the ML rules."""

from __future__ import annotations

from dataclasses import dataclass, field

EPS = 1e-9


@dataclass(frozen=True)
class Instance:
    """One balancing problem, already validated.

    times: task name -> time in minutes
    predecessors: task name -> names of direct predecessors
    cycle_time: minutes available per station per unit
    order: task names in the order the user entered them (used for stable tie-breaks)
    """

    times: dict[str, float]
    predecessors: dict[str, tuple[str, ...]]
    cycle_time: float
    order: tuple[str, ...]

    def successors(self) -> dict[str, tuple[str, ...]]:
        succ: dict[str, list[str]] = {name: [] for name in self.order}
        for name in self.order:
            for pred in self.predecessors[name]:
                succ[pred].append(name)
        return {name: tuple(items) for name, items in succ.items()}


@dataclass(frozen=True)
class Placement:
    """A task placed in a station. side is 'front' or 'back' (see placement.py)."""

    name: str
    side: str


@dataclass
class SolveOutcome:
    stations: list[list[Placement]]
    generations_run: int
    stop_reason: str  # "max_generations" | "stagnation" | "time_limit"
    best_fitness: float
    seed: int
    runtime_seconds: float
    # one entry per recorded generation: (generation, best_fitness, avg_fitness)
    convergence: list[tuple[int, float, float]] = field(default_factory=list)
