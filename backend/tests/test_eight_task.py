"""Second test case: the IE formulas document's 8-task example (section 8, cycle time 10).

Expected (IE document): 4 stations, efficiency 97.5%, balance delay 2.5%, smoothness index 1.00.
"""

from helpers import load_example

from app.ga.placement import check_solution
from app.schemas.problem import ProblemInput
from app.services.instance import summarize, to_instance
from app.services.solver import solve_problem


def _problem() -> ProblemInput:
    return ProblemInput.model_validate(load_example("eight_task_input.json"))


def test_eight_task_summary():
    summary = summarize(_problem())
    assert summary.task_count == 8
    assert summary.total_work_content == 39.0
    assert summary.cycle_time == 10.0
    assert summary.min_stations == 4


def test_ga_matches_ie_document_result():
    problem = _problem()
    result = solve_problem(problem)
    stations = [[t.name for t in s.tasks] for s in result.solution.stations]
    assert check_solution(to_instance(problem), stations) == []
    assert result.solution.num_stations == 4
    assert result.metrics.efficiency == 0.975
    assert result.metrics.balance_delay == 0.025
    assert result.metrics.smoothness_index == 1.0


def test_eight_task_run_end_to_end(client):
    created = client.post("/runs", json=load_example("eight_task_input.json"))
    assert created.status_code == 202
    status = client.get(f"/runs/{created.json()['run_id']}").json()
    assert status["status"] == "succeeded"
    metrics = status["result"]["metrics"]
    assert status["result"]["solution"]["num_stations"] == 4
    assert (metrics["efficiency"], metrics["balance_delay"], metrics["smoothness_index"]) == (
        0.975, 0.025, 1.0,
    )
