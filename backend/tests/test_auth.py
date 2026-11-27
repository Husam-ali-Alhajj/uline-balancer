"""Token verification (app/auth.py), with tokens signed by a key generated in the test."""

import time
import uuid

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tokens import TEST_URL, FakeJwks, bearer, make_token, use_test_project

from app import auth, config
from app.api.errors import register_error_handlers

app = FastAPI()
register_error_handlers(app)


@app.get("/whoami")
def whoami(user: auth.UserDep) -> dict:
    return {"user": str(user) if user else None}


client = TestClient(app)


def _code(response):
    return response.status_code, response.json()["error"]["code"]


def test_no_token_is_a_guest(monkeypatch):
    use_test_project(monkeypatch)
    assert client.get("/whoami").json() == {"user": None}


def test_valid_token_gives_the_user_id(monkeypatch):
    use_test_project(monkeypatch)
    user = uuid.uuid4()
    assert client.get("/whoami", headers=bearer(make_token(user))).json() == {"user": str(user)}


def test_leeway_accepts_a_token_that_expired_seconds_ago(monkeypatch):
    use_test_project(monkeypatch)
    assert client.get("/whoami", headers=bearer(make_token(expires_in=-10))).status_code == 200


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (lambda: make_token(expires_in=-120), (401, "expired_token")),
        (lambda: "not.a.token", (401, "invalid_token")),
        (lambda: "garbage", (401, "invalid_token")),
        (lambda: make_token(iss="https://evil.supabase.co/auth/v1"), (401, "invalid_token")),
        (lambda: make_token(aud="anon"), (401, "invalid_token")),
        (lambda: make_token(other_key=True), (401, "invalid_token")),  # wrong signature
        (lambda: make_token(algorithm="HS256"), (401, "invalid_token")),  # not on the allow-list
        (lambda: make_token(is_anonymous=True), (401, "invalid_token")),
        (lambda: make_token(sub="not-a-uuid"), (401, "invalid_token")),
        (lambda: make_token(iat=int(time.time()) + 600), (401, "invalid_token")),  # issued in the future
    ],
    ids=["expired", "malformed", "garbage", "wrong-issuer", "wrong-audience", "wrong-key", "hs256",
         "anonymous", "bad-sub", "future-iat"],
)
def test_bad_tokens_are_rejected_in_the_standard_format(monkeypatch, token, expected):
    use_test_project(monkeypatch)
    response = client.get("/whoami", headers=bearer(token()))
    assert _code(response) == expected
    assert response.json()["error"]["details"] == []


def test_unknown_key_id_is_invalid(monkeypatch):
    use_test_project(monkeypatch)
    token = jwt.encode({"sub": str(uuid.uuid4())}, "x" * 32, algorithm="HS256", headers={"kid": "nope"})
    assert _code(client.get("/whoami", headers=bearer(token))) == (401, "invalid_token")


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "Bearer   ", "token-without-scheme"])
def test_malformed_authorization_header(monkeypatch, header):
    use_test_project(monkeypatch)
    assert _code(client.get("/whoami", headers={"Authorization": header})) == (401, "invalid_token")


def test_key_page_unreachable_gives_503_but_guests_still_work(monkeypatch):
    use_test_project(monkeypatch, FakeJwks(fail=jwt.PyJWKClientConnectionError("timed out")))
    assert _code(client.get("/whoami", headers=bearer(make_token()))) == (503, "auth_unavailable")
    assert client.get("/whoami").json() == {"user": None}


def test_token_rejected_when_sign_in_is_not_configured(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "")
    assert _code(client.get("/whoami", headers=bearer(make_token()))) == (401, "invalid_token")
    assert client.get("/whoami").json() == {"user": None}


def test_key_client_uses_the_designed_settings(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", TEST_URL)
    keys = auth.jwks_client()
    assert keys.uri == f"{TEST_URL}/auth/v1/.well-known/jwks.json"
    assert keys.jwk_set_cache.lifespan == 600
    assert keys.timeout == 5
    assert auth.jwks_client() is keys  # one client, so the cache is shared


def test_tokens_are_never_logged(monkeypatch, caplog):
    use_test_project(monkeypatch)
    token = make_token(expires_in=-120)
    with caplog.at_level("DEBUG"):
        client.get("/whoami", headers=bearer(token))
        client.get("/whoami", headers=bearer(make_token()))
    assert token not in caplog.text
    assert token.split(".")[1] not in caplog.text
