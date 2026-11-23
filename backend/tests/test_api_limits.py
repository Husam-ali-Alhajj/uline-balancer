"""Inputs the API must reject with 422 in the standard error format, without internals (check G2)."""

import pytest


def _task(name, time, predecessors=()):
    return {"name": name, "time": time, "predecessors": list(predecessors)}


def _body(tasks, working=480, breaks=0, production=10):
    return {"tasks": tasks, "working_time_per_day": working, "break_time_per_day": breaks,
            "production_per_day": production}


BAD_INPUTS = {
    "break makes cycle time shorter than the longest task": _body(
        [_task("A", 8), _task("B", 4)], breaks=200, production=40),
    "51 tasks": _body([_task(f"T{i}", 1) for i in range(51)], working=50),
    "cycle in the precedence graph": _body(
        [_task("A", 1, ["C"]), _task("B", 1, ["A"]), _task("C", 1, ["B"])], working=20),
    "break equal to working time": _body([_task("A", 1)], breaks=480, production=1),
    "break above working time": _body([_task("A", 1)], breaks=500, production=1),
}


@pytest.mark.parametrize("case", BAD_INPUTS)
def test_rejected_with_standard_error(client, case):
    response = client.post("/runs", json=BAD_INPUTS[case])
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]
    assert "Traceback" not in response.text and 'File "' not in response.text
