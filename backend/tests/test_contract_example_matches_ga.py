"""The six-task contract examples must be the GA's real output (A.2.2).

The frontend mocks are built from these files, so this test keeps them honest: if the GA,
the metrics or the result format change, regenerate the examples from a real run."""

from helpers import load_example


def _without_runtime(result: dict) -> dict:
    ga = {k: v for k, v in result["ga"].items() if k != "runtime_seconds"}
    return {**result, "ga": ga}


def test_six_task_result_example_is_real_ga_output(client):
    created = client.post("/runs", json=load_example("six_task_input.json"))
    assert created.status_code == 202
    status = client.get(f"/runs/{created.json()['run_id']}").json()
    assert status["status"] == "succeeded"

    assert _without_runtime(status["result"]) == _without_runtime(load_example("six_task_result.json"))


def test_succeeded_status_example_carries_the_same_result():
    status = load_example("six_task_run_status_succeeded.json")
    assert status["result"] == load_example("six_task_result.json")
    assert status["progress"]["generation"] == status["result"]["ga"]["generations_run"]
