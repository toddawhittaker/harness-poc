"""identity-stub — fake identity provider, real RS256 tokens (SPEC §4.1).

Stands in for Microsoft Entra ID. The personas are fake and the passwords are
literally "demo", but the tokens are real: RS256-signed, with a published JWKS
that every other service fetches and checks independently.

Swapping this for Entra changes the issuer and adds the on-behalf-of exchange.
No enforcement code downstream changes.

This service mints tokens and never verifies them, so it deliberately does not
depend on libs/harness_auth. It makes no audit calls either — nothing here has
an authenticated identity to record yet.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Any

import jwt
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ISSUER = os.environ["JWT_ISSUER"]
AUDIENCE = os.environ["JWT_AUDIENCE"]
PERSONAS_PATH = Path(os.environ.get("PERSONAS_PATH", "/config/personas.yaml"))
KEY_DIR = Path(os.environ.get("KEY_DIR", "/data"))
KEY_PATH = KEY_DIR / "jwt_private.pem"
TOKEN_TTL_SECONDS = 8 * 60 * 60

app = FastAPI(title="identity-stub")


class TokenRequest(BaseModel):
    persona: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = TOKEN_TTL_SECONDS


class Persona(BaseModel):
    id: str
    name: str


def load_personas() -> dict[str, dict[str, Any]]:
    with PERSONAS_PATH.open() as handle:
        return yaml.safe_load(handle)["personas"]


def load_or_create_key() -> rsa.RSAPrivateKey:
    """Generated on first boot into the data volume, so tokens survive restarts."""
    if KEY_PATH.exists():
        # Re-assert the mode on load, not only at creation: a key restored from
        # a backup, or written by an earlier container running as root, would
        # otherwise keep whatever permissions it arrived with.
        KEY_PATH.chmod(0o600)
        return serialization.load_pem_private_key(KEY_PATH.read_bytes(), password=None)

    KEY_DIR.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    KEY_PATH.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    KEY_PATH.chmod(0o600)
    return key


def b64u(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


PERSONAS = load_personas()
PRIVATE_KEY = load_or_create_key()
PUBLIC_NUMBERS = PRIVATE_KEY.public_key().public_numbers()
KID = hashlib.sha256(
    PRIVATE_KEY.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
).hexdigest()[:16]
PRIVATE_PEM = PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/personas", response_model=list[Persona])
def personas() -> list[Persona]:
    """Ids and display names only. Passwords never leave this process."""
    return [Persona(id=pid, name=data["name"]) for pid, data in PERSONAS.items()]


@app.post("/token", response_model=TokenResponse)
def token(request: TokenRequest) -> TokenResponse:
    persona = PERSONAS.get(request.persona)
    # Same 401 for an unknown persona as for a bad password, so the response
    # does not confirm which personas exist.
    #
    # Compare bytes, not str: hmac.compare_digest raises TypeError on a str
    # containing non-ASCII, which would turn a wrong password into an
    # unhandled 500 on an unauthenticated endpoint.
    expected = "" if persona is None else str(persona["password"])
    if not hmac.compare_digest(request.password.encode(), expected.encode()) or persona is None:
        raise HTTPException(status_code=401, detail="Invalid persona or password")

    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": request.persona,
        "name": persona["name"],
        "roles": list(persona["roles"]),
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    access_token = jwt.encode(claims, PRIVATE_PEM, algorithm="RS256", headers={"kid": KID})
    return TokenResponse(access_token=access_token)


@app.get("/jwks.json")
def jwks() -> dict[str, list[dict[str, str]]]:
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": KID,
                "n": b64u(PUBLIC_NUMBERS.n),
                "e": b64u(PUBLIC_NUMBERS.e),
            }
        ]
    }
