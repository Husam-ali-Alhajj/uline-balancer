"""Tests for the GA loop (docs/GA_DESIGN.md sections 6 and 7). Every result must pass check_solution."""

import random

from helpers import instance_from_input, load_example

from app.ga.engine import solve
from app.ga.placement import check_solution
from app.ga.types import Instance


def _six():
    return instance_from_input(load_example("six_task_input.json"))


def _names(outcome):
    return [[p.name for p in station] for station in outcome.stations]


def _random_instance(rng: random.Random) -> Instance:
    n = rng.randint(1, 20)
    cycle = float(rng.randint(5, 20))
    names = [f"T{i}" for i in range(n)]
    predecessors = {
        name: tuple(p for p in names[:i] if rng.random() < 0.3) for i, name in enumerate(names)
    }
    order = names[:]
    rng.shuffle(order)
    return Instance(
        times={name: float(rng.randint(1, int(cycle))) for name in names},
        predecessors=predecessors,
        cycle_time=cycle,
        order=tuple(order),
    )


def test_six_task_example_gives_three_stations():
    inst = _six()
    outcome = solve(inst, {}, seed=42)
    assert check_solution(inst, _names(outcome)) == []
    assert len(outcome.stations) == 3
    assert outcome.best_fitness < 4


def test_same_seed_gives_same_result():
    inst = _six()
    a = solve(inst, {}, seed=123)
    b = solve(inst, {}, seed=123)
    assert _names(a) == _names(b)
    assert [[p.side for p in s] for s in a.stations] == [[p.side for p in s] for s in b.stations]
    assert a.best_fitness == b.best_fitness
    assert a.convergence == b.convergence
    assert a.generations_run == b.generations_run
    assert a.seed == b.seed == 123


def test_missing_seed_is_drawn_and_reported():
    inst = _six()
    first = solve(inst, {}, seed=None)
    again = solve(inst, {}, seed=first.seed)
    assert _names(first) == _names(again)


def test_random_instances_are_always_feasible():
    rng = random.Random(2026)
    for _ in range(60):
        inst = _random_instance(rng)
        settings = {"population_size": 10, "max_generations": 10, "stagnation_limit": 5}
        outcome = solve(inst, settings, seed=rng.randrange(1000))
        assert check_solution(inst, _names(outcome)) == []


def test_convergence_best_never_gets_worse():
    outcome = solve(_six(), {"stagnation_limit": 1000}, seed=5)
    best = [b for _, b, _ in outcome.convergence]
    assert best == sorted(best, reverse=True)
    assert outcome.convergence[-1][1] == outcome.best_fitness
    assert [g for g, _, _ in outcome.convergence] == list(range(outcome.generations_run + 1))


def test_stops_at_max_generations():
    outcome = solve(_six(), {"max_generations": 10, "stagnation_limit": 1000}, seed=1)
    assert outcome.stop_reason == "max_generations"
    assert outcome.generations_run == 10
    assert len(outcome.convergence) == 11


def test_stops_on_stagnation():
    outcome = solve(_six(), {"max_generations": 1000, "stagnation_limit": 5}, seed=1)
    assert outcome.stop_reason == "stagnation"
    assert outcome.generations_run < 1000


def test_time_limit_still_returns_a_valid_solution():
    inst = _six()
    outcome = solve(inst, {}, seed=1, time_limit_s=0.0)
    assert outcome.stop_reason == "time_limit"
    assert outcome.generations_run == 0
    assert check_solution(inst, _names(outcome)) == []


def test_elitism_larger_than_population_is_capped():
    inst = _six()
    settings = {"population_size": 10, "elitism_count": 50, "max_generations": 10}
    outcome = solve(inst, settings, seed=3)
    assert check_solution(inst, _names(outcome)) == []


def test_progress_is_reported_every_generation():
    calls = []
    outcome = solve(_six(), {"max_generations": 10, "stagnation_limit": 1000}, seed=1,
                    progress=lambda g, m: calls.append((g, m)))
    assert calls == [(g, 10) for g in range(outcome.generations_run + 1)]
