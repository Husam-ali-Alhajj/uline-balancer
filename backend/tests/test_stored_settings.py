"""Stored runs load with loose settings: a saved result is never re-checked against today's GASettings
limits (which may have changed since it was saved). Incoming requests still use the strict limits."""

import copy
import uuid
from datetime import UTC, datetime

from helpers import load_example

from app.db.models import Run
from app.db.session import SessionLocal

RESULT = load_example("six_task_run_status_succeeded.json")["result"]


def _store(settings: dict) -> str:
    result = copy.deepcopy(RESULT)
    result["ga"]["settings"] = settings
    run = Run(id=uuid.uuid4(), title="saved earlier", status="succeeded", input=load_example("six_task_input.json"),
              result=result, created_at=datetime.now(UTC), finished_at=datetime.now(UTC))
    with SessionLocal() as session:
        session.add(run)
        session.commit()
    return str(run.id)


def test_stored_result_with_out_of_range_settings_loads(client):
    settings = {**RESULT["ga"]["settings"], "tournament_size": 50}  # today's limit is 20, and <= population
    response = client.get(f"/runs/{_store(settings)}")
    assert response.status_code == 200
    assert response.json()["result"]["ga"]["settings"]["tournament_size"] == 50


def test_stored_result_with_a_missing_or_extra_setting_loads(client):
    settings = {k: v for k, v in RESULT["ga"]["settings"].items() if k != "stagnation_limit"}
    settings["old_setting"] = 1  # a setting that no longer exists
    response = client.get(f"/runs/{_store(settings)}")
    assert response.status_code == 200


def test_incoming_requests_keep_the_strict_limits(client):
    body = load_example("six_task_input.json") | {"ga_settings": {"tournament_size": 50}}
    response = client.post("/runs", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
