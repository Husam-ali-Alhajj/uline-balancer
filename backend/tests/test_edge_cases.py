"""A.1.8: edge cases through validation, the GA and the full solver. Every result passes check_solution."""

from app.ga.engine import solve
from app.ga.placement import check_solution
from app.schemas.problem import ProblemInput
from app.services.instance import to_instance
from app.services.solver import solve_problem


def _problem(spec, cycle_time: int) -> ProblemInput:
    """spec: (name, time, predecessors); cycle time = 480 / production, so it must divide 480."""
    return ProblemInput.model_validate({
        "tasks": [{"name": n, "time": t, "predecessors": p} for n, t, p in spec],
        "working_time_per_day": 480,
        "production_per_day": 480 // cycle_time,
        "ga_settings": {"seed": 7},
    })


def _run(problem: ProblemInput):
    result = solve_problem(problem)
    stations = [[t.name for t in s.tasks] for s in result.solution.stations]
    assert check_solution(to_instance(problem), stations) == []
    return result, stations


def test_single_task():
    # one task: max(t) <= C <= sum(t) forces C = t
    result, stations = _run(_problem([("A", 5, [])], 5))
    assert stations == [["A"]]
    assert result.metrics.efficiency == 1.0
    assert result.metrics.smoothness_index == 0.0
    assert result.metrics.idle_time_variation == 0.0
    assert result.metrics.gap_to_minimum == 0.0


def test_pure_chain():
    spec = [("A", 2, []), ("B", 4, ["A"]), ("C", 3, ["B"]),
            ("D", 3, ["C"]), ("E", 2, ["D"]), ("F", 4, ["E"])]
    result, _ = _run(_problem(spec, 6))
    assert result.instance.min_stations == 3
    assert result.solution.num_stations == 3
    assert result.metrics.efficiency == 1.0


def test_no_precedence():
    spec = [("A", 5, []), ("B", 1, []), ("C", 4, []), ("D", 2, []), ("E", 3, []), ("F", 3, [])]
    result, stations = _run(_problem(spec, 6))
    assert result.solution.num_stations == 3
    assert all(t.side == "front" for s in result.solution.stations for t in s.tasks)
    assert sorted(sorted(s) for s in stations) == [["A", "B"], ["C", "D"], ["E", "F"]]


def test_task_equal_to_cycle_time():
    spec = [("A", 3, []), ("B", 6, ["A"]), ("C", 3, ["B"])]
    result, stations = _run(_problem(spec, 6))
    assert ["B"] in stations  # a full-cycle task is always alone
    assert result.solution.num_stations == 2
    full = next(s for s in result.solution.stations if [t.name for t in s.tasks] == ["B"])
    assert full.idle == 0.0
    assert full.utilization == 1.0


def test_every_task_equal_to_cycle_time():
    spec = [("A", 4, []), ("B", 4, ["A"]), ("C", 4, [])]
    result, stations = _run(_problem(spec, 4))
    assert result.solution.num_stations == 3
    assert all(len(s) == 1 for s in stations)


def test_fifty_task_run_is_feasible_and_bounded():
    names = [f"T{i}" for i in range(50)]
    spec = [(n, 1 + (i * 7) % 9, [names[i - 1]] if i % 5 else []) for i, n in enumerate(names)]
    problem = _problem(spec, 12)
    outcome = solve(to_instance(problem), problem.ga_settings.model_dump(), seed=7)
    stations = [[p.name for p in s] for s in outcome.stations]
    assert check_solution(to_instance(problem), stations) == []
    assert outcome.runtime_seconds < 30
