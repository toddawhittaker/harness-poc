"""Token verification, done the same way by every service (SPEC §2).

This is shared *code*, not a shared runtime. Each service imports it and runs
its own check against its own copy of the JWKS. No service trusts the fact that
an upstream service already validated the same token — that independence is the
architectural claim the whole POC exists to demonstrate.

Note on the filename: SPEC §2 names this module jwt.py, and it imports the
PyJWT package, also called jwt. Python 3 uses absolute imports, so `import jwt`
below resolves to PyJWT and not to this module.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request
from jwt import PyJWTError
from pydantic import BaseModel

from .audit import audit_event

JWKS_URL = os.environ.get("HARNESS_JWKS_URL", "http://identity-stub:8001/jwks.json")
ISSUER = os.environ.get("HARNESS_JWT_ISSUER", "http://identity-stub:8001")
AUDIENCE = os.environ.get("HARNESS_JWT_AUDIENCE", "harness-poc")

# Pinned, not read from the token header. A verifier that honours the header's
# `alg` accepts alg:none, and accepts an HS256 token whose HMAC secret is the
# published public key. Both are in tests/test_auth.py.
ALGORITHMS = ["RS256"]

# A token with no `exp` never expires; one with no `sub` names nobody. Neither
# is "unconstrained", both are invalid.
REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub"]

JWKS_TIMEOUT_SECONDS = 5.0

# `kid` comes from an unverified token header, so refetching on every unknown
# one lets anyone turn each service into a load generator against identity-stub.
JWKS_MIN_REFETCH_SECONDS = 30.0

# Nothing here is a secret: the JWKS holds public keys only.
_keys: dict[str, Any] = {}
_keys_lock = asyncio.Lock()
_last_fetch = 0.0


class AuthError(Exception):
    """Any reason a token is not acceptable. Always becomes a 401."""


class Claims(BaseModel):
    """The verified claim set. Constructing one means the checks passed."""

    sub: str
    name: str
    roles: list[str] = []
    iss: str
    # `str` is deliberately strict for the POC. The JWT spec allows a list
    # audience and Entra can emit one, so the MVP version must widen this.
    # Do not "fix" it now.
    aud: str
    iat: int
    exp: int


async def _load_jwks() -> None:
    """Fetch and parse the JWKS. Every failure becomes AuthError, never a 500.

    Parsing is inside the try on purpose: a malformed document (a bare array, a
    string where a key object belongs, an RSA entry missing `n`) raises
    AttributeError, ValueError, or InvalidKeyError, none of which are
    PyJWTError. Unreachable while identity-stub is the issuer — and exactly the
    shape that bites when the issuer becomes somebody else's.
    """
    try:
        async with httpx.AsyncClient(timeout=JWKS_TIMEOUT_SECONDS) as client:
            response = await client.get(JWKS_URL)
            response.raise_for_status()
            document = response.json()

        loaded: dict[str, Any] = {}
        for key in document.get("keys", []):
            if key.get("kty") != "RSA" or not key.get("kid"):
                continue
            loaded[key["kid"]] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    except Exception as exc:  # noqa: BLE001
        raise AuthError("signing keys are unavailable") from exc

    if not loaded:
        raise AuthError("signing keys are unavailable")

    # No await between clear() and update(): the event loop cannot switch
    # tasks here, so readers never see the empty in-between state. Do not
    # insert awaited calls between these two lines.
    _keys.clear()
    _keys.update(loaded)


async def _key_for(kid: str) -> Any:
    """Cached public key for `kid`, refetching for a kid we have not seen.

    The refetch is what makes key rotation survivable without a restart. It is
    rate limited because `kid` is attacker-controlled: without the limit, a
    flood of tokens carrying random key ids turns every validating service into
    an amplifier pointed at identity-stub. The cost of the limit is that a
    genuine rotation takes up to JWKS_MIN_REFETCH_SECONDS to be picked up.
    """
    global _last_fetch

    if kid not in _keys:
        async with _keys_lock:
            if kid not in _keys:
                # Accepted trade-off: a failed fetch still burns the window, so a stub
                # outage can mean up to 30s of unknown-kid rejections after recovery —
                # rate-limiting attempts rather than successes is intentional.
                elapsed = time.monotonic() - _last_fetch
                if elapsed >= JWKS_MIN_REFETCH_SECONDS:
                    _last_fetch = time.monotonic()
                    await _load_jwks()

    key = _keys.get(kid)
    if key is None:
        raise AuthError("token was signed with an unknown key id")
    return key


async def verify_token(token: str) -> Claims:
    """Verify signature, issuer, audience, and expiry. Raise AuthError on any failure.

    There is no path through this function that returns Claims without every
    check having passed.
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:  # noqa: BLE001 — same reasoning as the decode below
        raise AuthError("token is malformed") from exc

    kid = header.get("kid")
    if not kid:
        raise AuthError("token header carries no key id")

    key = await _key_for(kid)

    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": REQUIRED_CLAIMS},
        )
    except PyJWTError as exc:
        # PyJWT's messages name the failed check ("Signature has expired",
        # "Invalid audience", ...) and never quote the token, so they are safe
        # to record and genuinely useful on the audit page.
        raise AuthError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        # Not every way PyJWT can reject a token is a PyJWTError. Feeding it a
        # key of the wrong type for the header's algorithm raises a bare
        # TypeError, and PyJWKClientError sits outside InvalidTokenError. A
        # failure to verify is an authentication failure, never a 500 with a
        # stack trace and no audit row.
        raise AuthError("token could not be verified") from exc

    try:
        return Claims(**claims)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("token claims are not the expected shape") from exc


async def bearer_claims(request: Request) -> Claims:
    """FastAPI dependency: verified Claims, or a 401 with an audit row.

    Used by the gateway now and by the orchestrator in Session 2. The MCP
    servers call verify_token directly from their own middleware — same check,
    different transport.
    """
    header = request.headers.get("authorization") or ""
    scheme, _, credential = header.partition(" ")
    if scheme.lower() != "bearer" or not credential.strip():
        await audit_event(
            "auth_failed",
            detail={"reason": "Authorization header missing or malformed"},
        )
        raise _unauthorized("Not authenticated")

    try:
        return await verify_token(credential.strip())
    except AuthError as exc:
        await audit_event("auth_failed", detail={"reason": str(exc)})
        raise _unauthorized("Invalid or expired token") from exc


def _unauthorized(detail: str) -> HTTPException:
    """A 401 that says nothing about the credential it just rejected."""
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": 'Bearer realm="harness-poc"'},
    )
