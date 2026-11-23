"""The IE document's 8-task example (section 8) over many seeds (Sprint 1 check E3).

Expected values come from the IE document: 4 stations, E = 97.5%, d = 2.5%, SI = 1.00.
"""

import pytest
from helpers import load_example

from app.ga.placement import check_solution
from app.schemas.problem import ProblemInput
from app.services.instance import to_instance
from app.services.solver import solve_problem


@pytest.mark.parametrize("seed", range(20))
def test_eight_task_example_for_seed(seed):
    data = load_example("eight_task_input.json")
    data["ga_settings"]["seed"] = seed
    problem = ProblemInput.model_validate(data)
    result = solve_problem(problem)
    stations = [[t.name for t in s.tasks] for s in result.solution.stations]
    assert check_solution(to_instance(problem), stations) == []
    assert result.solution.num_stations == 4
    assert result.metrics.efficiency == 0.975
    assert result.metrics.balance_delay == 0.025
    assert result.metrics.smoothness_index == 1.0
