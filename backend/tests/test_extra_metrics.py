"""A.1.7: idle-time variation (LV) and gap to the minimum (MASTER.md section 5).

LV = sqrt(sum((C - ST_j)^2) / N); Gap = (N - N_min) / N_min. Both are optional result fields.
"""

import math

from helpers import instance_from_input, load_example

from app.ga.metrics import compute_metrics
from app.schemas.problem import ProblemInput
from app.services.instance import summarize
from app.services.solver import solve_problem


def test_lv_and_gap_match_hand_calculation():
    # C = 8, loads 8, 8, 7: idle 0, 0, 1 -> LV = sqrt(1/3); N = N_min = 3 -> gap 0
    m = compute_metrics(8.0, [8, 8, 7], min_stations=3)
    assert m.idle_time_variation == round(math.sqrt(1 / 3), 4) == 0.5774
    assert m.gap_to_minimum == 0.0


def test_gap_with_extra_stations():
    # C = 10, loads 10, 3, 3, 2 with N_min = 2: idle 0, 7, 7, 8 -> LV = sqrt(162/4)
    m = compute_metrics(10.0, [10, 3, 3, 2], min_stations=2)
    assert m.gap_to_minimum == 1.0
    assert m.idle_time_variation == round(math.sqrt(162 / 4), 4)


def test_gap_is_none_without_min_stations():
    assert compute_metrics(8.0, [8, 8, 7]).gap_to_minimum is None


def test_perfect_balance_has_zero_lv():
    assert compute_metrics(5.0, [5, 5, 5], min_stations=3).idle_time_variation == 0.0


def test_solver_result_includes_both_fields():
    for name, lv in (("six_task_input.json", 0.5774), ("eight_task_input.json", 0.5)):
        problem = ProblemInput.model_validate(load_example(name))
        metrics = solve_problem(problem).metrics
        assert metrics.idle_time_variation == lv
        assert metrics.gap_to_minimum == 0.0


def test_example_files_agree_with_metrics():
    data = load_example("six_task_input.json")
    instance = instance_from_input(data)
    min_stations = summarize(ProblemInput.model_validate(data)).min_stations
    for name in ("six_task_result.json", "six_task_run_status_succeeded.json"):
        example = load_example(name)
        result = example.get("result", example)
        loads = [s["load"] for s in result["solution"]["stations"]]
        m = compute_metrics(instance.cycle_time, loads, min_stations)
        assert result["metrics"]["idle_time_variation"] == m.idle_time_variation
        assert result["metrics"]["gap_to_minimum"] == m.gap_to_minimum


def test_run_api_returns_both_fields(client):
    created = client.post("/runs", json=load_example("six_task_input.json"))
    metrics = client.get(f"/runs/{created.json()['run_id']}").json()["result"]["metrics"]
    assert metrics["idle_time_variation"] == 0.5774
    assert metrics["gap_to_minimum"] == 0.0
