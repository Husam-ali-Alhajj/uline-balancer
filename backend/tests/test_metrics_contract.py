"""LV and gap on a non-optimal solution, and old stored results without them (Sprint 1 check F2, F5)."""

import json

from helpers import CONTRACTS, instance_from_input, load_example
from jsonschema import Draft202012Validator

from app.ga.metrics import compute_metrics
from app.ga.placement import check_solution
from app.schemas.result import RunResult
from app.schemas.run import RunStatus

NEW_FIELDS = ("idle_time_variation", "gap_to_minimum")


def _schema(name):
    return json.loads((CONTRACTS / name).read_text())


def test_forced_five_station_eight_task_solution():
    inst = instance_from_input(load_example("eight_task_input.json"))
    stations = [["A"], ["B", "C"], ["E", "F"], ["G", "H"], ["D"]]
    assert check_solution(inst, stations) == []
    loads = [sum(inst.times[x] for x in s) for s in stations]
    m = compute_metrics(inst.cycle_time, loads, min_stations=4)
    assert m.gap_to_minimum == 0.25
    # IE document section 8 reports LV = 3.43 for a 5-station line with these idle times
    assert m.idle_time_variation == 3.4351


def test_eight_task_optimal_loads():
    m = compute_metrics(10.0, [10, 10, 10, 9], min_stations=4)
    assert (m.idle_time_variation, m.gap_to_minimum) == (0.5, 0.0)


def test_old_result_without_new_fields_still_validates():
    result = load_example("six_task_result.json")
    for field in NEW_FIELDS:
        del result["metrics"][field]
    Draft202012Validator(_schema("run_result.schema.json")).validate(result)
    parsed = RunResult.model_validate(result)
    assert parsed.metrics.idle_time_variation is None
    assert parsed.metrics.gap_to_minimum is None


def test_old_run_status_without_new_fields_still_validates():
    status = load_example("six_task_run_status_succeeded.json")
    for field in NEW_FIELDS:
        del status["result"]["metrics"][field]
    Draft202012Validator(_schema("run_status.schema.json")).validate(status)
    RunStatus.model_validate(status)
