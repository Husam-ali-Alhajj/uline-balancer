"""Tests for the pure GA modules: placement rule, checker, metrics, fitness, skeleton engine."""

from helpers import instance_from_input, load_example

from app.ga.engine import solve
from app.ga.fitness import compute_fitness
from app.ga.metrics import compute_metrics
from app.ga.placement import check_solution, place_station


def _inst():
    return instance_from_input(load_example("six_task_input.json"))


def test_cycle_time_of_example():
    assert _inst().cycle_time == 8.0


def test_known_good_solution_is_feasible():
    assert check_solution(_inst(), [["A", "F"], ["B", "C"], ["D", "E"]]) == []


def test_u_rule_allows_last_task_in_first_station():
    placed = place_station(_inst(), ["A", "F"], set())
    assert [(p.name, p.side) for p in placed] == [("A", "front"), ("F", "back")]


def test_checker_rejects_overloaded_station():
    problems = check_solution(_inst(), [["A", "B", "C"], ["D", "E", "F"]])
    assert any("exceeds cycle time" in p for p in problems)


def test_checker_rejects_missing_and_duplicate_tasks():
    assert any("not assigned" in p for p in check_solution(_inst(), [["A"], ["B", "C"]]))
    assert any("appears in" in p for p in check_solution(_inst(), [["A", "A"]]))


def test_checker_rejects_precedence_violation():
    # D needs (B and C) or (F) assigned first; here neither holds in station 1
    problems = check_solution(_inst(), [["D", "A"], ["B", "C"], ["E", "F"]])
    assert any("U-line precedence" in p for p in problems)


def test_metrics_match_hand_calculation():
    m = compute_metrics(8.0, [8, 8, 7])
    assert m.efficiency == 0.9583
    assert m.balance_delay == 0.0417
    assert m.total_idle_time == 1.0
    assert m.smoothness_index == 1.0
    assert m.bottleneck_stations == [1, 2]
    assert m.high_idle_stations == []


def test_high_idle_station_is_flagged():
    assert compute_metrics(10.0, [10, 10, 3]).high_idle_stations == [3]


def test_fitness_never_lets_smoothness_outweigh_a_station():
    assert compute_fitness(3, 1.0, 8.0) == 3.0417
    # worst possible smoothness for 3 stations is sqrt(3) * cycle_time
    worst_three = compute_fitness(3, (3**0.5) * 8.0, 8.0)
    best_four = compute_fitness(4, 0.0, 8.0)
    assert worst_three < best_four


def test_skeleton_engine_returns_feasible_solution():
    inst = _inst()
    outcome = solve(inst, {"max_generations": 100}, seed=7)
    names = [[p.name for p in station] for station in outcome.stations]
    assert check_solution(inst, names) == []
    assert outcome.seed == 7


def test_skeleton_engine_is_reproducible():
    inst = _inst()
    a = solve(inst, {}, seed=1)
    b = solve(inst, {}, seed=1)
    assert [[p.name for p in s] for s in a.stations] == [[p.name for p in s] for s in b.stations]
