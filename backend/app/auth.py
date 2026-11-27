"""Sign-in token verification (docs/DECISIONS.md, "User accounts design", point 3).

A request may send `Authorization: Bearer <Supabase access token>`. No header: a guest (None). A header
that fails any check is rejected with 401 (expired_token or invalid_token), never treated as a guest.
The token is checked here, locally, with the project's public keys (ES256); the keys are fetched and
cached by PyJWT's PyJWKClient. If they cannot be fetched, a request with a token gets 503
auth_unavailable. Tokens are never logged.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header

from app import config
from app.api.errors import ApiError

ALGORITHMS = ["ES256"]  # fixed allow-list: the token header can never choose the algorithm
AUDIENCE = "authenticated"
LEEWAY_S = 30  # clock difference allowed between our server and Supabase
JWKS_LIFESPAN_S = 600  # same as Supabase's own cache of the key page
JWKS_TIMEOUT_S = 5

_jwks: jwt.PyJWKClient | None = None
_jwks_url: str | None = None


def issuer() -> str:
    return f"{config.SUPABASE_URL}/auth/v1"


def jwks_client() -> jwt.PyJWKClient:
    """One client per process, so its key cache is shared by all requests."""
    global _jwks, _jwks_url
    url = f"{issuer()}/.well-known/jwks.json"
    if _jwks is None or _jwks_url != url:
        _jwks = jwt.PyJWKClient(url, lifespan=JWKS_LIFESPAN_S, timeout=JWKS_TIMEOUT_S)
        _jwks_url = url
    return _jwks


def _invalid() -> ApiError:
    return ApiError(401, "invalid_token", "The sign-in token is not valid. Please sign in again.")


def verify_token(token: str) -> uuid.UUID:
    """Return the user id (the `sub` claim) of a valid token, or raise ApiError."""
    if not config.SUPABASE_URL:
        raise _invalid()  # sign-in is not configured on this server
    try:
        key = jwks_client().get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError:
        raise ApiError(503, "auth_unavailable",
                       "Sign-in cannot be checked right now. Try again shortly.") from None
    except jwt.PyJWTError:  # malformed token, or a key id the project does not have
        raise _invalid() from None
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=issuer(),
            leeway=LEEWAY_S,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "expired_token", "The sign-in token has expired. Please sign in again.") from None
    except jwt.PyJWTError:
        raise _invalid() from None
    if claims.get("is_anonymous") is True:  # Supabase anonymous sign-ins are not accepted
        raise _invalid()
    try:
        return uuid.UUID(str(claims["sub"]))
    except ValueError:
        raise _invalid() from None


def current_user(authorization: Annotated[str | None, Header()] = None) -> uuid.UUID | None:
    """FastAPI dependency: the signed-in user's id, or None for a guest."""
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _invalid()
    return verify_token(token.strip())


UserDep = Annotated[uuid.UUID | None, Depends(current_user)]
