"""Test tokens, signed by an ES256 key generated here (never a real Supabase key)."""

import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app import auth, config

TEST_URL = "https://test-project.supabase.co"
_key = ec.generate_private_key(ec.SECP256R1())
_other_key = ec.generate_private_key(ec.SECP256R1())  # a key the "project" does not publish
KID = "test-key"


class FakeJwks:
    """Stands in for PyJWKClient: knows only our test public key."""

    def __init__(self, fail: Exception | None = None):
        self.fail = fail

    def get_signing_key_from_jwt(self, token: str):
        if self.fail:
            raise self.fail
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise jwt.PyJWKClientError("Unable to find a signing key that matches")
        return jwt.PyJWK.from_dict({**jwt.algorithms.ECAlgorithm.to_jwk(_key.public_key(), as_dict=True),
                                    "kid": KID, "alg": "ES256"})


def make_token(sub=None, *, expires_in=3600, iss=None, aud="authenticated", other_key=False,
               algorithm="ES256", **extra) -> str:
    now = int(time.time())
    claims = {"sub": str(sub or uuid.uuid4()), "iss": iss or f"{TEST_URL}/auth/v1", "aud": aud,
              "iat": now, "exp": now + expires_in, "role": "authenticated", **extra}
    if algorithm == "HS256":
        return jwt.encode(claims, "x" * 32, algorithm="HS256", headers={"kid": KID})
    return jwt.encode(claims, _other_key if other_key else _key, algorithm="ES256", headers={"kid": KID})


def use_test_project(monkeypatch, jwks=None):
    monkeypatch.setattr(config, "SUPABASE_URL", TEST_URL)
    monkeypatch.setattr(auth, "jwks_client", lambda: jwks or FakeJwks())


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
