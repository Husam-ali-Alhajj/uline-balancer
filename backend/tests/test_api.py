"""End-to-end API tests (inline executor, temporary SQLite database)."""

import copy

from app.ga.placement import check_solution

from helpers import instance_from_input, load_example


def _body() -> dict:
    return copy.deepcopy(load_example("six_task_input.json"))


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_validate_returns_summary(client):
    res = client.post("/validate", json=_body())
    assert res.status_code == 200
    assert res.json()["instance"] == {
        "task_count": 6, "total_work_content": 23.0, "cycle_time": 8.0, "min_stations": 3,
    }


def test_invalid_input_uses_standard_error_format(client):
    body = _body()
    body["tasks"][0]["predecessors"] = ["F"]  # cycle
    res = client.post("/runs", json=body)
    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]


def test_run_lifecycle(client):
    created = client.post("/runs", json=_body())
    assert created.status_code == 202
    run_id = created.json()["run_id"]

    status = client.get(f"/runs/{run_id}").json()
    assert status["status"] == "succeeded"
    assert status["error"] is None

    stations = [[t["name"] for t in s["tasks"]] for s in status["result"]["solution"]["stations"]]
    assert check_solution(instance_from_input(_body()), stations) == []

    listed = client.get("/runs").json()
    assert any(item["run_id"] == run_id for item in listed)

    assert client.delete(f"/runs/{run_id}").status_code == 204
    assert client.get(f"/runs/{run_id}").status_code == 404


def test_unknown_run_is_404_in_standard_format(client):
    res = client.get("/runs/not-a-uuid")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"
