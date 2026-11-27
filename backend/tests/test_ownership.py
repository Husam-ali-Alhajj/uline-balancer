"""Runs are scoped to their owner (docs/DECISIONS.md, "User accounts design", points 1 and 2)."""

import uuid

import pytest
from helpers import load_example
from tokens import bearer, make_token, use_test_project

from app.db.models import Run
from app.db.session import SessionLocal

BODY = load_example("six_task_input.json")


@pytest.fixture
def users(monkeypatch):
    use_test_project(monkeypatch)
    return bearer(make_token(uuid.uuid4())), bearer(make_token(uuid.uuid4()))


def _create(client, headers=None) -> str:
    created = client.post("/runs", json=BODY, headers=headers or {})
    assert created.status_code == 202
    return created.json()["run_id"]


def _not_found(response) -> bool:
    return response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_create_stores_the_owner(client, users):
    a, _ = users
    run_id = _create(client, a)
    with SessionLocal() as session:
        assert session.get(Run, uuid.UUID(run_id)).owner_id is not None
    guest_id = _create(client)
    with SessionLocal() as session:
        assert session.get(Run, uuid.UUID(guest_id)).owner_id is None


def test_users_see_only_their_own_runs(client, users):
    a, b = users
    run_a, run_b = _create(client, a), _create(client, b)
    listed_a = [r["run_id"] for r in client.get("/runs", headers=a).json()]
    listed_b = [r["run_id"] for r in client.get("/runs", headers=b).json()]
    assert listed_a == [run_a] and listed_b == [run_b]

    # B cannot read or delete A's run, and gets the same answer as for a run that does not exist
    assert _not_found(client.get(f"/runs/{run_a}", headers=b))
    assert _not_found(client.delete(f"/runs/{run_a}", headers=b))
    assert _not_found(client.get(f"/runs/{run_a}"))  # nor can a guest
    assert _not_found(client.delete(f"/runs/{run_a}"))
    assert client.get(f"/runs/{run_a}", headers=a).status_code == 200  # still there for A

    assert client.delete(f"/runs/{run_a}", headers=a).status_code == 204
    assert _not_found(client.get(f"/runs/{run_a}", headers=a))


def test_guest_run_works_by_id_and_is_never_listed(client, users):
    a, _ = users
    guest_run = _create(client)
    assert client.get(f"/runs/{guest_run}").json()["status"] == "succeeded"
    assert client.get(f"/runs/{guest_run}", headers=a).status_code == 200  # anyone with the id
    assert client.get("/runs").json() == []
    assert guest_run not in [r["run_id"] for r in client.get("/runs", headers=a).json()]
    # nobody can delete a guest run through the API (404, like any run the caller may not delete)
    assert _not_found(client.delete(f"/runs/{guest_run}"))
    assert _not_found(client.delete(f"/runs/{guest_run}", headers=a))
    assert client.get(f"/runs/{guest_run}").status_code == 200


@pytest.mark.parametrize("method", ["get_list", "post", "get", "delete"])
def test_bad_token_is_rejected_on_every_endpoint(client, users, method):
    a, _ = users
    run_id = _create(client, a)
    expired = bearer(make_token(expires_in=-120))
    calls = {
        "get_list": lambda: client.get("/runs", headers=expired),
        "post": lambda: client.post("/runs", json=BODY, headers=expired),
        "get": lambda: client.get(f"/runs/{run_id}", headers=expired),
        "delete": lambda: client.delete(f"/runs/{run_id}", headers=expired),
    }
    response = calls[method]()
    assert (response.status_code, response.json()["error"]["code"]) == (401, "expired_token")


def test_rejected_token_does_not_create_a_guest_run(client, users):
    with SessionLocal() as session:
        before = session.query(Run).count()
    client.post("/runs", json=BODY, headers=bearer("not.a.token"))
    with SessionLocal() as session:
        assert session.query(Run).count() == before
