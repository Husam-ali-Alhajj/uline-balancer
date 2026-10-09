import copy

import pytest
from pydantic import ValidationError

from app.schemas.problem import MAX_TASKS, ProblemInput

from helpers import load_example


def _data() -> dict:
    return copy.deepcopy(load_example("six_task_input.json"))


def test_valid_example_parses():
    assert ProblemInput.model_validate(_data()).cycle_time == 8.0


def _expect_error(data: dict, fragment: str) -> None:
    with pytest.raises(ValidationError) as exc:
        ProblemInput.model_validate(data)
    assert fragment in str(exc.value)


def test_duplicate_task_names():
    data = _data()
    data["tasks"][1]["name"] = "A"
    _expect_error(data, "duplicate task names")


def test_unknown_predecessor():
    data = _data()
    data["tasks"][1]["predecessors"] = ["Z"]
    _expect_error(data, "unknown predecessor")


def test_self_predecessor():
    data = _data()
    data["tasks"][1]["predecessors"] = ["B"]
    _expect_error(data, "own predecessor")


def test_cycle_is_rejected():
    data = _data()
    data["tasks"][0]["predecessors"] = ["F"]
    _expect_error(data, "cycle")


def test_task_longer_than_cycle_time():
    data = _data()
    data["tasks"][0]["time"] = 9.0
    _expect_error(data, "longer than the cycle time")


def test_non_positive_values():
    for key, value in (("production_per_day", 0), ("working_time_per_day", 0)):
        data = _data()
        data[key] = value
        with pytest.raises(ValidationError):
            ProblemInput.model_validate(data)


def test_too_many_tasks():
    data = _data()
    data["tasks"] = [{"name": f"T{i}", "time": 1.0, "predecessors": []} for i in range(MAX_TASKS + 1)]
    with pytest.raises(ValidationError):
        ProblemInput.model_validate(data)


def test_unknown_field_is_rejected():
    data = _data()
    data["surprise"] = 1
    with pytest.raises(ValidationError):
        ProblemInput.model_validate(data)
