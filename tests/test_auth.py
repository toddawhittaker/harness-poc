"""Negative-auth tests — the only mandatory test file (SPEC §6).

Written before the validation code exists. They gate every stage: nothing in
this repo is "done" while one of them is red, and no check may be softened to
turn one green.

HOW THESE TESTS GET BAD TOKENS — AND WHY THAT DOES NOT MIGRATE
--------------------------------------------------------------
The correctly-signed-but-wrong tokens here (expired, wrong `aud`, wrong `iss`,
missing claims) are signed in-process with identity-stub's own RSA private key,
read from the host side of the ./data bind mount. That is deliberate: it makes
each test fail on exactly the claim under test, instead of collapsing every
case into "bad signature" and proving far less. It is honest for a POC whose
issuer is a stub we own end to end.

It does not survive the move to production, and nobody should try to make it.
In the MVP the issuer is Microsoft Entra ID: the private key lives in Entra,
nothing in this repository can sign a token, and there is no PEM on disk to
read. A test that needs one is a test asking for a private key that must not
exist. When that swap happens, this file splits in two:

  * The claim-level cases (exp, aud, iss, missing claims, alg:none, the HS256
    algorithm-confusion attack) become UNIT tests of `verify_token` against a
    fixture JWKS and locally generated throwaway keys — no live services, no
    real issuer, nothing borrowed from the identity provider.
  * Only the cases that need no signing key stay as live integration tests:
    no token, malformed Authorization header, and the tampered/foreign
    signature.

POC-honest now, different mechanics later. Do not port the PEM-reading trick.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import importlib.util
import json
import logging
import socket
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from conftest import (
    AUDIENCE,
    AUDIT_URL,
    CHAT_TIMEOUT_SECONDS,
    IDENTITY_URL,
    ISSUER,
    MCP_PATH,
    MCP_SERVERS,
    ORCHESTRATOR_URL,
    PERSONA_NAMES,
    PERSONA_ROLES,
    REPO_ROOT,
    TOKEN_TTL_SECONDS,
    base_claims,
    decode_jsonrpc,
    fetch_events,
    mcp_initialize_request,
    mcp_session,
    pick_id_outside,
    post_chat,
    post_chat_with_token,
    raw_chat_status,
    request_token,
    rsa_key_from_jwks,
    student_ids_in,
    utcnow,
    wait_for_event,
    walk_keys,
    walk_values,
)

# Refusal wording the spec fixes exactly (SPEC §4.4, §4.6). Asserted verbatim.
DEAN_INDIVIDUAL_RECORD_REFUSAL = (
    "Individual student records require an advisor assignment; deans receive aggregates."
)
NOOR_FOREIGN_SECTION = "BUS-201-A"
FOREIGN_SECTION_REFUSAL = (
    "Section BUS-201-A is not among your assigned sections; "
    "cross-section views belong to the dean."
)


# --------------------------------------------------------------------------
# Byte-level JWS construction. pyjwt refuses to build these on purpose — an
# unsigned token and an RSA public key used as an HMAC secret are both attacks,
# not valid usage — so the attack tests assemble them by hand.
# --------------------------------------------------------------------------


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def signing_input(header: dict[str, Any], claims: dict[str, Any]) -> str:
    def encode(part: dict[str, Any]) -> str:
        return b64url(json.dumps(part, separators=(",", ":"), sort_keys=True).encode())

    return f"{encode(header)}.{encode(claims)}"


def unsigned_token(claims: dict[str, Any], kid: str) -> str:
    """An `alg: none` token: real claims, no signature at all."""
    return signing_input({"alg": "none", "typ": "JWT", "kid": kid}, claims) + "."


def hs256_token(claims: dict[str, Any], secret: bytes, kid: str) -> str:
    """The algorithm-confusion attack: sign with HMAC-SHA256 using the server's
    own RSA PUBLIC key as the shared secret. A verifier that trusts the header's
    `alg` will happily accept it, because the public key is public."""
    payload = signing_input({"alg": "HS256", "typ": "JWT", "kid": kid}, claims)
    signature = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest()
    return f"{payload}.{b64url(signature)}"


def mutate_signature(token: str) -> str:
    """Flip the first character of the signature segment.

    The first character carries real signature bits; the last one is mostly
    base64 padding and flipping it can decode to identical bytes.
    """
    header, payload, signature = token.split(".")
    flipped = "B" if signature[0] != "B" else "C"
    return f"{header}.{payload}.{flipped}{signature[1:]}"


def assert_unauthorized(response: httpx.Response, what: str) -> None:
    assert response.status_code == 401, (
        f"{what} must be rejected with 401. Got {response.status_code}: {response.text[:200]}"
    )


# ==========================================================================
# Session 1 — these gate everything. Unmarked, so they run by default.
# ==========================================================================

# --------------------------------------------------------------------------
# No credential, or a credential the gateway cannot even parse.
# --------------------------------------------------------------------------


def test_missing_authorization_header_is_rejected(http: httpx.Client) -> None:
    response = post_chat(http, authorization=None)
    assert_unauthorized(response, "a request with no Authorization header")


@pytest.mark.parametrize(
    "header_value",
    [
        pytest.param("", id="empty-header-value"),
        pytest.param("Bearer", id="scheme-with-no-token"),
        pytest.param("Basic ZGFuYTpkZW1v", id="non-bearer-scheme-basic"),
        pytest.param("Token abc.def.ghi", id="non-bearer-scheme-token"),
    ],
)
def test_malformed_authorization_header_is_rejected(http: httpx.Client, header_value: str) -> None:
    response = post_chat(http, authorization=header_value)
    assert_unauthorized(response, f"Authorization: {header_value!r}")


@pytest.mark.parametrize(
    "header_value",
    [
        pytest.param("Bearer ", id="scheme-with-trailing-space"),
        pytest.param("Bearer\t", id="scheme-with-trailing-tab"),
        pytest.param("bearer   ", id="lowercase-scheme-trailing-spaces"),
    ],
)
def test_authorization_header_with_trailing_whitespace_is_rejected(header_value: str) -> None:
    """A credential that is nothing but whitespace once the scheme is stripped.

    These go over a raw socket because RFC 9110 forbids trailing whitespace in a
    field value, so httpx refuses to put them on the wire (LocalProtocolError).
    An attacker writing bytes to a socket has no such scruples, so the guarantee
    is worth asserting rather than dropping.

    What this proves is the end-to-end behavior, which is the right level for an
    integration test. It does not reach the application's own `.strip()`: h11
    normalizes optional whitespace out of a field value, so all three variants
    arrive at `bearer_claims` as bare `Bearer`/`bearer` — the same code path as
    the `scheme-with-no-token` case above. The stack as a whole answers 401,
    which is the promise being kept.

    This is the only place in the suite that bypasses httpx, and it does so to
    make the test stricter, never to make one pass.
    """
    status = raw_chat_status(header_value)
    assert status == 401, (
        f"Authorization: {header_value!r} must be rejected with 401, got {status}"
    )


def test_valid_token_without_the_bearer_prefix_is_rejected(
    http: httpx.Client, dana_token: str
) -> None:
    """A perfectly good token is still not a credential if it arrives bare."""
    response = post_chat(http, authorization=dana_token)
    assert_unauthorized(response, "a raw token sent with no 'Bearer ' prefix")


# --------------------------------------------------------------------------
# Signature. The token is well formed; the maths must not add up.
# --------------------------------------------------------------------------


def test_token_signed_by_a_foreign_key_is_rejected(
    http: httpx.Client, mint: Callable[..., str], foreign_private_key: RSAPrivateKey
) -> None:
    """Correct claims, correct `kid`, signed by a key the harness never saw.

    The kid is the real one on purpose: the server finds the right public key,
    and the only thing that fails is the signature.
    """
    token = mint(key=foreign_private_key)
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, "a token signed by a key the harness does not trust")


def test_token_with_a_mutated_signature_is_rejected(http: httpx.Client, dana_token: str) -> None:
    tampered = mutate_signature(dana_token)
    assert tampered != dana_token, "the tamper helper did not change the token"
    response = post_chat_with_token(http, tampered)
    assert_unauthorized(response, "a real token with one byte flipped in its signature")


def test_unsigned_alg_none_token_is_rejected(
    http: httpx.Client, signing_kid: str
) -> None:
    token = unsigned_token(base_claims("dana"), signing_kid)
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, "an unsigned token claiming alg:none")


def test_hs256_token_signed_with_the_public_key_is_rejected(
    http: httpx.Client, public_key_pem: bytes, signing_kid: str
) -> None:
    """Algorithm confusion: if the verifier honours the header's `alg` instead
    of pinning RS256, anyone holding the published public key can mint tokens."""
    token = hs256_token(base_claims("dana"), public_key_pem, signing_kid)
    response = post_chat_with_token(http, token)
    assert_unauthorized(
        response,
        "an HS256 token whose HMAC secret is the server's own public key "
        "(the verifier must pin RS256, not trust the header's alg)",
    )


# --------------------------------------------------------------------------
# Claims. Correctly signed, and still wrong.
# --------------------------------------------------------------------------


def test_expired_token_is_rejected(http: httpx.Client, mint: Callable[..., str]) -> None:
    issued = int(time.time()) - TOKEN_TTL_SECONDS - 3600
    token = mint(claims={"iat": issued, "exp": issued + TOKEN_TTL_SECONDS})
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, "a correctly signed token whose exp is an hour in the past")


def test_token_for_a_different_audience_is_rejected(
    http: httpx.Client, mint: Callable[..., str]
) -> None:
    token = mint(claims={"aud": "some-other-api"})
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, f"a token with aud='some-other-api' instead of {AUDIENCE!r}")


def test_token_from_a_different_issuer_is_rejected(
    http: httpx.Client, mint: Callable[..., str]
) -> None:
    token = mint(claims={"iss": "http://evil-idp.example.com"})
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, f"a token with iss='http://evil-idp.example.com' instead of {ISSUER!r}")


@pytest.mark.parametrize("claim", ["exp", "sub"])
def test_token_missing_a_required_claim_is_rejected(
    http: httpx.Client, mint: Callable[..., str], claim: str
) -> None:
    """A token with no `exp` never expires; a token with no `sub` names nobody.
    Both must be refused rather than treated as unconstrained."""
    token = mint(drop=[claim])
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, f"a correctly signed token with no {claim!r} claim")


def test_gateway_401_does_not_echo_the_token(http: httpx.Client, mint: Callable[..., str]) -> None:
    issued = int(time.time()) - TOKEN_TTL_SECONDS - 3600
    token = mint(claims={"iat": issued, "exp": issued + TOKEN_TTL_SECONDS})
    response = post_chat_with_token(http, token)
    assert_unauthorized(response, "an expired token")
    assert token not in response.text, "the 401 body repeated the rejected token back to the caller"
    assert "eyJ" not in response.text, f"the 401 body contains a JWT-shaped string: {response.text[:200]}"


# --------------------------------------------------------------------------
# The positive control. Without this, every test above could pass on a
# gateway that simply 401s everything.
# --------------------------------------------------------------------------


def test_valid_token_reaches_the_gateway(http: httpx.Client, dana_token: str) -> None:
    """What this proves: dana's real token is ACCEPTED and the request is served.

    That is the whole job. Every test above asserts a 401, and all of them would
    pass just as happily on a gateway that answered 401 to everything — this is
    the one test that says the accepting path exists at all.

    It asserts nothing about the content of the answer. Session 2 removed ECHO
    mode (SPEC §8): the gateway now triages the question and forwards the
    survivors to the orchestrator, so the reply is whatever a model wrote and
    there is no fixed string to look for. The shape is still contractual — a
    non-empty `reply` string and a `tools_used` list — and the status code is
    what carries the authentication claim.

    The message is deliberately not a real question. Triage classifies it as
    `other` and the gateway answers from the gate in about two seconds, which
    keeps the suite's positive control cheap. Whether the gate answers or the
    orchestrator does is irrelevant here; both are 200, and 200 is the claim.
    Tests that need the full path to run say so explicitly, and cost ten seconds.
    """
    response = post_chat_with_token(http, dana_token, "negative-auth suite positive control")
    assert response.status_code == 200, (
        f"dana's freshly minted token must be accepted. Got {response.status_code}: "
        f"{response.text[:200]}"
    )
    body = response.json()
    assert isinstance(body.get("reply"), str) and body["reply"], f"no reply in {body!r}"
    assert isinstance(body.get("tools_used"), list), (
        f"tools_used must be a list, got {type(body.get('tools_used')).__name__}: {body!r}"
    )


# --------------------------------------------------------------------------
# identity-stub (SPEC §4.1).
# --------------------------------------------------------------------------


def test_wrong_password_gets_no_token(http: httpx.Client) -> None:
    response = request_token(http, "dana", password="not-the-password")
    assert_unauthorized(response, "a token request for dana with the wrong password")
    assert "access_token" not in response.text


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("dëmo", id="latin-1-accent"),
        pytest.param("demo’", id="smart-quote"),
        pytest.param("\U0001f512", id="emoji"),
    ],
)
def test_non_ascii_password_is_rejected_not_crashed(http: httpx.Client, password: str) -> None:
    """A wrong password must be a 401, whatever bytes it is made of.

    hmac.compare_digest raises TypeError on a str holding non-ASCII, so
    comparing str to str turns a wrong password into an unhandled 500 on an
    unauthenticated endpoint.
    """
    response = request_token(http, "dana", password=password)
    assert response.status_code == 401, (
        f"a non-ASCII password must be rejected with 401, not {response.status_code}: "
        f"{response.text[:200]}"
    )


def test_unknown_persona_gets_no_token(http: httpx.Client) -> None:
    response = request_token(http, "mallory")
    assert_unauthorized(response, "a token request for a persona that does not exist")
    assert "access_token" not in response.text


def test_personas_endpoint_exposes_ids_and_names_and_nothing_else(http: httpx.Client) -> None:
    response = http.get(f"{IDENTITY_URL}/personas")
    assert response.status_code == 200, f"GET /personas returned {response.status_code}"
    personas = response.json()
    assert isinstance(personas, list), "GET /personas must return a JSON array"
    assert {persona["id"] for persona in personas} == set(PERSONA_ROLES), (
        f"GET /personas listed {[p.get('id') for p in personas]}, expected {sorted(PERSONA_ROLES)}"
    )
    for persona in personas:
        assert set(persona) == {"id", "name"}, (
            f"persona {persona.get('id')!r} exposes extra fields {sorted(set(persona) - {'id', 'name'})}; "
            "SPEC §4.1 says ids and display names only"
        )
        assert persona["name"] == PERSONA_NAMES[persona["id"]]
    body = response.text.lower()
    assert "password" not in body, "GET /personas mentions a password field"
    assert "demo" not in body, "GET /personas leaks the shared demo password"


def test_jwks_publishes_one_public_rs256_key(jwks: dict[str, Any]) -> None:
    keys = jwks["keys"]
    assert len(keys) == 1, (
        f"expected exactly one published key, found {len(keys)}; the bad-token tests need an "
        "unambiguous kid"
    )
    key = keys[0]
    assert key.get("kty") == "RSA", f"kty must be RSA, got {key.get('kty')!r}"
    assert key.get("alg", "RS256") == "RS256", f"alg must be RS256, got {key.get('alg')!r}"
    assert key.get("use", "sig") == "sig", f"use must be sig, got {key.get('use')!r}"
    assert key.get("kid"), "the published key carries no kid"
    private_parameters = sorted({"d", "p", "q", "dp", "dq", "qi"} & set(key))
    assert not private_parameters, (
        f"jwks.json is publishing PRIVATE key material: {private_parameters}"
    )


@pytest.mark.parametrize("persona", sorted(PERSONA_ROLES))
def test_minted_token_verifies_against_the_published_jwks(
    http: httpx.Client, jwks: dict[str, Any], token_for: Callable[[str], str], persona: str
) -> None:
    """Verify a real token the way every service must: JWKS signature, iss, aud."""
    token = token_for(persona)
    kid = jwt.get_unverified_header(token).get("kid")
    assert kid, "identity-stub minted a token with no kid in the header"
    claims = jwt.decode(
        token,
        key=rsa_key_from_jwks(jwks, kid),
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )
    assert claims["sub"] == persona
    assert claims["name"] == PERSONA_NAMES[persona]
    assert claims["roles"] == PERSONA_ROLES[persona], (
        f"{persona}'s token carries roles {claims['roles']!r}, "
        f"config/personas.yaml says {PERSONA_ROLES[persona]!r}"
    )
    lifetime = claims["exp"] - claims["iat"]
    assert abs(lifetime - TOKEN_TTL_SECONDS) <= 2, (
        f"token lifetime is {lifetime}s, SPEC §3 says {TOKEN_TTL_SECONDS}s"
    )


# --------------------------------------------------------------------------
# Audit (SPEC §4.8). Every 401 leaves a row; every completed request does too.
# --------------------------------------------------------------------------

AUDIT_ROW_FIELDS = {"ts", "service", "event", "sub", "roles", "detail"}


def test_audit_timestamps_are_iso8601_with_a_timezone(http: httpx.Client) -> None:
    """Runs first among the audit tests on purpose.

    The viewer orders rows by ts and so does this suite's polling helper. A
    naive timestamp is ambiguous the moment anything runs in another zone, and
    it would make every audit test below fail with the misleading complaint
    that no row was written.
    """
    since = utcnow() - timedelta(seconds=2)
    assert_unauthorized(post_chat(http, authorization=None), "a request with no Authorization header")
    event = wait_for_event(http, lambda row: row.get("event") == "auth_failed", since=since)
    assert event is not None, (
        "no auth_failed row appeared after a rejected request. If the gateway does write one, "
        "check its ts: rows timestamped outside this test's window are invisible to the poller."
    )
    for row in fetch_events(http, limit=25):
        raw = row.get("ts")
        assert isinstance(raw, str) and raw, f"audit row has no ts: {row!r}"
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00").replace("z", "+00:00"))
        assert parsed.tzinfo is not None, (
            f"audit ts {raw!r} carries no timezone; use datetime.now(timezone.utc).isoformat()"
        )


def test_gateway_auth_failure_is_audited(http: httpx.Client) -> None:
    since = utcnow() - timedelta(seconds=2)
    response = post_chat(http, authorization=None)
    assert_unauthorized(response, "a request with no Authorization header")

    event = wait_for_event(
        http,
        lambda row: row.get("service") == "gateway" and row.get("event") == "auth_failed",
        since=since,
    )
    assert event is not None, (
        "the gateway rejected the request but wrote no auth_failed audit row (SPEC §4.2)"
    )
    assert AUDIT_ROW_FIELDS <= set(event), (
        f"audit row is missing fields {sorted(AUDIT_ROW_FIELDS - set(event))} (SPEC §4.8)"
    )


def test_successful_chat_is_audited(http: httpx.Client, dana_token: str) -> None:
    """A real question is required now, and the question has to fit the persona.

    SPEC §4.2 gives the gateway two exits, and only one of them writes the row
    this test is looking for. Step 3 audits `refused_at_gate` and answers from
    the gate; step 5 audits `request_completed` after the orchestrator has run.
    Anything triage classifies as `other` — "audit me", "hello", small talk —
    takes the first exit and never reaches the second. That is correct
    behaviour, so the fix belongs in the question, not in the assertion.

    dana is an advisor, so an advisee question passes triage and drives the full
    gateway -> orchestrator -> MCP path. It calls a live model and takes roughly
    ten seconds; CHAT_TIMEOUT_SECONDS is why it does not hit the client default.
    """
    since = utcnow() - timedelta(seconds=2)
    response = post_chat_with_token(
        http,
        dana_token,
        "Which of my advisees have not logged in recently?",
        timeout=CHAT_TIMEOUT_SECONDS,
    )
    assert response.status_code == 200, f"expected 200, got {response.status_code}"

    event = wait_for_event(
        http,
        lambda row: (
            row.get("service") == "gateway"
            and row.get("event") == "request_completed"
            and row.get("sub") == "dana"
        ),
        since=since,
    )
    assert event is not None, (
        "a successful /chat wrote no request_completed audit row for dana (SPEC §4.2 step 5)"
    )
    assert event.get("roles") == PERSONA_ROLES["dana"], (
        f"audit row recorded roles {event.get('roles')!r}, expected {PERSONA_ROLES['dana']!r}"
    )


SYNTHETIC_JWT = (
    "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZha2UifQ"
    ".eyJzdWIiOiJub2JvZHkiLCJhdWQiOiJoYXJuZXNzLXBvYyJ9"
    ".c3ludGhldGljLXNpZ25hdHVyZS1mb3ItdGhlLXNjcnViLXRlc3Q"
)


@pytest.mark.parametrize(
    "detail",
    [
        pytest.param({"authorization": f"Bearer {SYNTHETIC_JWT}"}, id="sensitive-key-at-top-level"),
        pytest.param(
            {"upstream": {"authorization": f"Bearer {SYNTHETIC_JWT}"}},
            id="sensitive-key-nested-one-level",
        ),
        pytest.param(
            {"context": {"request": {"headers": {"Authorization": f"Bearer {SYNTHETIC_JWT}"}}}},
            id="sensitive-key-nested-three-deep",
        ),
        pytest.param(
            {"headers": f"Authorization: Bearer {SYNTHETIC_JWT}"},
            id="token-in-a-value-under-an-innocent-key",
        ),
        pytest.param({"trace": [f"Bearer {SYNTHETIC_JWT}"]}, id="token-inside-a-list"),
        pytest.param({"note": f"raw token {SYNTHETIC_JWT}"}, id="bare-token-in-prose"),
    ],
)
def test_audit_strips_credentials_from_any_shape_of_detail(
    http: httpx.Client, detail: dict[str, Any]
) -> None:
    """The audit service is the backstop for a careless caller.

    Checking only top-level key names catches the one mistake nobody makes.
    A token arrives nested, inside a list, or dumped whole into a value under a
    perfectly innocent key.
    """
    since = utcnow() - timedelta(seconds=2)
    marker = f"scrub-probe-{abs(hash(json.dumps(detail, sort_keys=True))) % 10**8}"
    posted = http.post(
        f"{AUDIT_URL}/events",
        json={
            "service": "test-harness",
            "event": "tool_call",
            "sub": "nobody",
            "roles": [],
            "detail": {**detail, "probe": marker},
        },
    )
    assert posted.status_code == 204, f"POST /events returned {posted.status_code}"

    row = wait_for_event(
        http,
        lambda event: event.get("detail", {}).get("probe") == marker,
        since=since,
    )
    assert row is not None, "the probe event was never stored"

    stored = json.dumps(row)
    assert SYNTHETIC_JWT not in stored, (
        f"the token survived scrubbing and is now in the audit trail: {stored[:300]}"
    )
    assert "eyJ" not in stored, f"a JWT-shaped string survived scrubbing: {stored[:300]}"
    for value in walk_values(row):
        assert "bearer " not in value.lower(), (
            f"an Authorization header survived scrubbing: {value[:120]!r}"
        )


def test_audit_keeps_legitimate_fields_whose_names_merely_contain_token(
    http: httpx.Client,
) -> None:
    """Redaction must not silently eat real data.

    Session 2 records model usage. If the marker list matches substrings,
    prompt_tokens and completion_tokens vanish while the row claims a
    redaction happened — worse than either keeping or dropping them honestly.
    """
    since = utcnow() - timedelta(seconds=2)
    marker = "usage-probe"
    posted = http.post(
        f"{AUDIT_URL}/events",
        json={
            "service": "test-harness",
            "event": "answer_returned",
            "sub": "nobody",
            "roles": [],
            "detail": {"probe": marker, "prompt_tokens": 812, "completion_tokens": 140},
        },
    )
    assert posted.status_code == 204

    row = wait_for_event(
        http, lambda event: event.get("detail", {}).get("probe") == marker, since=since
    )
    assert row is not None, "the usage probe was never stored"
    detail = row["detail"]
    assert detail.get("prompt_tokens") == 812 and detail.get("completion_tokens") == 140, (
        f"token-count fields were dropped as if they were credentials: {detail!r}"
    )
    assert "redacted_fields" not in detail, (
        f"nothing sensitive was sent, but the row claims a redaction: {detail!r}"
    )


FORBIDDEN_AUDIT_KEYS = {"authorization", "password", "access_token", "token", "bearer", "jwt"}


def test_audit_never_records_tokens_or_credentials(
    http: httpx.Client, dana_token: str, mint: Callable[..., str]
) -> None:
    """Duty 4: tokens must never reach a log or an audit detail field.

    Generate traffic in both directions first — one accepted request carrying a
    real token, one rejected request carrying a well-formed expired one — so the
    scan runs against rows that were written while tokens were in hand.

    The accepted request asks a genuine advisee question rather than a throwaway
    one, for two reasons. It has to survive triage at all: SPEC §4.2 answers
    anything classified `other` from the gate, and the `request_completed` row
    this waits on is only written after the orchestrator has run. And it is the
    stronger scan — the caller's bearer travels gateway -> orchestrator -> four
    MCP servers, and every one of those hops writes audit rows while holding the
    token. A question that stops at the gate would never exercise them.

    The scanning assertions below are unchanged and must stay exactly this
    strict. They are the point of the test; the question is only the setup.
    """
    since = utcnow() - timedelta(seconds=2)
    accepted = post_chat_with_token(
        http,
        dana_token,
        "Which of my advisees have not logged in recently?",
        timeout=CHAT_TIMEOUT_SECONDS,
    )
    assert accepted.status_code == 200, f"expected 200, got {accepted.status_code}"

    issued = int(time.time()) - TOKEN_TTL_SECONDS - 3600
    expired = mint(claims={"iat": issued, "exp": issued + TOKEN_TTL_SECONDS})
    assert_unauthorized(post_chat_with_token(http, expired), "an expired token")

    completed = wait_for_event(
        http,
        lambda row: row.get("event") == "request_completed" and row.get("sub") == "dana",
        since=since,
    )
    failed = wait_for_event(
        http,
        lambda row: row.get("event") == "auth_failed",
        since=since,
    )
    assert completed is not None and failed is not None, (
        "expected both a request_completed and an auth_failed row before scanning for leaks"
    )

    events = fetch_events(http, limit=200)
    serialized = json.dumps(events)
    assert "eyJ" not in serialized, (
        "a JWT-shaped string (eyJ...) appears in GET /events — a token reached the audit trail"
    )
    assert dana_token not in serialized, "dana's live token appears verbatim in the audit trail"
    assert expired not in serialized, "the rejected token appears verbatim in the audit trail"

    for key in walk_keys(events):
        assert key.lower() not in FORBIDDEN_AUDIT_KEYS, (
            f"audit rows carry a field named {key!r}; credentials must never be recorded"
        )
    for value in walk_values(events):
        assert "bearer " not in value.lower(), (
            f"an audit value contains an Authorization header: {value[:120]!r}"
        )


# --------------------------------------------------------------------------
# The dropped-event breadcrumb (SPEC §2). Tested in-process — no containers.
# --------------------------------------------------------------------------

AUDIT_MODULE_PATH = REPO_ROOT / "libs" / "harness_auth" / "src" / "harness_auth" / "audit.py"

# Planted in both the detail payload and the URL's query string. Neither may
# reach the log line.
LEAK_MARKER = "MUST-NOT-BE-LOGGED"


@pytest.fixture
def audit_module() -> Any:
    """harness_auth.audit, loaded straight from the file.

    Importing the package would pull harness_auth.jwt and with it fastapi and
    pydantic, which this workspace deliberately does not carry — only pytest,
    httpx, pyjwt and cryptography. audit.py needs nothing beyond httpx, so
    loading the file directly exercises the real code without widening the
    test workspace's dependencies.

    A fresh module per test also gives each one a clean debounce timestamp.
    """
    spec = importlib.util.spec_from_file_location("harness_auth_audit_under_test", AUDIT_MODULE_PATH)
    assert spec is not None and spec.loader is not None, f"cannot load {AUDIT_MODULE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _probe_payload() -> dict[str, Any]:
    return {
        "service": "test-harness",
        "event": "auth_failed",
        "sub": "dana",
        "roles": ["advisor"],
        "detail": {"reason": LEAK_MARKER},
    }


def test_a_dropped_audit_event_warns_once_and_leaks_nothing(
    audit_module: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """A real host answering 404 — the misconfiguration that looked like success.

    Before `raise_for_status`, a HARNESS_AUDIT_URL pointing at some other
    service's 404 was silent twice over: nothing recorded, nothing logged, and
    an audit page that was simply, inexplicably empty.

    The URL carries a marker in its query string and the payload carries the
    same marker in `detail`. httpx puts the full request URL, query included,
    into HTTPStatusError's message — so logging the exception's message rather
    than its class is exactly how a credential would reach the log.
    """
    audit_module.AUDIT_URL = f"{IDENTITY_URL}/nonexistent?token={LEAK_MARKER}"

    with caplog.at_level(logging.WARNING, logger="harness_auth.audit"):
        for _ in range(3):
            # Returning at all is the assertion that nothing escapes.
            asyncio.run(audit_module._post(_probe_payload()))

    records = [r for r in caplog.records if r.name == "harness_auth.audit"]
    assert len(records) == 1, (
        f"expected exactly one warning from three failed posts (debounced to "
        f"once per {audit_module.LOG_DEBOUNCE_SECONDS:.0f}s), got {len(records)}: "
        f"{[r.getMessage() for r in records]}"
    )

    message = records[0].getMessage()
    assert records[0].levelno == logging.WARNING, f"expected WARNING, got {records[0].levelname}"
    assert "auth_failed" in message, f"the line does not name the dropped event: {message!r}"
    assert "HTTPStatusError" in message, (
        f"the line does not name the exception class: {message!r}"
    )
    assert LEAK_MARKER not in message, (
        f"the line leaked the detail payload or the URL's query string: {message!r}"
    )
    assert "?" not in message, f"the URL's query string was not stripped: {message!r}"


def test_the_dropped_event_warning_resumes_after_the_debounce_window(
    audit_module: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Debounced, not silenced after the first one.

    Winding the module's timestamp back is how this stays a fast test rather
    than a sixty-second one.
    """
    audit_module.AUDIT_URL = f"{IDENTITY_URL}/nonexistent"

    with caplog.at_level(logging.WARNING, logger="harness_auth.audit"):
        asyncio.run(audit_module._post(_probe_payload()))
        asyncio.run(audit_module._post(_probe_payload()))          # suppressed
        audit_module._last_warned -= audit_module.LOG_DEBOUNCE_SECONDS + 1
        asyncio.run(audit_module._post(_probe_payload()))          # window reopened

    records = [r for r in caplog.records if r.name == "harness_auth.audit"]
    assert len(records) == 2, (
        "a dead audit service must keep warning once the window reopens; "
        f"expected 2 warnings, got {len(records)}"
    )


def test_a_successful_audit_post_logs_nothing(
    audit_module: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """The negative control: without it, a _post that always warned would pass."""
    audit_module.AUDIT_URL = f"{AUDIT_URL}/events"

    with caplog.at_level(logging.WARNING, logger="harness_auth.audit"):
        asyncio.run(audit_module._post(_probe_payload()))

    records = [r for r in caplog.records if r.name == "harness_auth.audit"]
    assert not records, f"a successful post warned anyway: {[r.getMessage() for r in records]}"


# --------------------------------------------------------------------------
# Auditing must never change the outcome of a request (SPEC §2).
#
# Disruptive: this stops and restarts the audit container. It is deliberately
# the LAST Session 1 test, so no test that needs audit rows runs during the
# outage — events emitted while audit is down are lost, by design.
# --------------------------------------------------------------------------


def _compose(*args: str) -> None:
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"`docker compose {' '.join(args)}` failed ({result.returncode}): "
        f"{result.stderr.strip()[:300]}"
    )


# Wider than harness_auth.audit's LOG_DEBOUNCE_SECONDS. If the gateway process
# warned shortly before this test ran, the new warning is suppressed and the
# earlier one must still be inside the window, or the search fails for a reason
# that has nothing to do with the behavior under test.
def _compose_logs(*services: str, since: str = "180s") -> str:
    result = subprocess.run(
        ["docker", "compose", "logs", "--since", since, *services],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout + result.stderr


def _wait_for_log(needle: str, *services: str, timeout: float = 10.0) -> str | None:
    """Poll container logs for `needle`. The audit POST is a background task,
    so the line lands shortly after the response, not before it."""
    deadline = time.monotonic() + timeout
    while True:
        logs = _compose_logs(*services)
        for line in logs.splitlines():
            if needle in line:
                return line
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.5)


def _wait_for_audit(client: httpx.Client, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if client.get(f"{AUDIT_URL}/healthz", timeout=2.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    pytest.fail(
        f"audit did not come back within {timeout}s. The suite left it stopped — "
        "run `docker compose up -d audit` before rerunning.",
        pytrace=False,
    )


@pytest.mark.disruptive
def test_authentication_survives_the_audit_service_being_down(
    http: httpx.Client, dana_token: str
) -> None:
    """A dead audit service must not change what the gateway answers.

    `bearer_claims` audits the auth failure *before* raising its 401, so if
    audit_event ever went back to awaiting the POST, this path would inherit
    the audit service's availability and its latency. That is the failure this
    guards: an audit trail that can take authentication down is a liability,
    not a control.

    Note what the timing assertion does and does not prove. A stopped container
    means connection-refused or a DNS miss, both of which fail fast, so this
    does not simulate a *hung* audit service. It is a regression guard: if the
    fire-and-forget scheduling were reverted to an awaited POST, a black-holed
    audit service would stall this path for TIMEOUT_SECONDS, and the margin
    below is well inside that.
    """
    _compose("stop", "audit")
    try:
        started = time.monotonic()
        rejected = post_chat(http, authorization=None)
        elapsed = time.monotonic() - started

        assert rejected.status_code == 401, (
            "with audit down, an unauthenticated request must still be a clean 401, "
            f"not {rejected.status_code}: {rejected.text[:200]}"
        )
        assert elapsed < 1.0, (
            f"the 401 took {elapsed:.2f}s with audit down; authentication must not "
            "wait on the audit service (SPEC §2 — audit_event never blocks)"
        )

        # The accepted path must be unaffected too: auditing changes no outcome.
        accepted = post_chat_with_token(http, dana_token, "audit is down")
        assert accepted.status_code == 200, (
            "with audit down, a valid token must still be accepted, got "
            f"{accepted.status_code}: {accepted.text[:200]}"
        )

        # A dropped event must leave a breadcrumb. Demo moment 9 is the audit
        # page; if it is ever empty because the URL is wrong or the container
        # died, this line is the difference between a ten-second fix during
        # setup and debugging live in front of the room.
        line = _wait_for_log("audit event", "gateway")
        assert line is not None, (
            "audit was down and events were dropped, but the gateway logged nothing. "
            "An empty audit page must never be a silent failure — see harness_auth.audit."
        )
        assert "dropped" in line, f"unexpected audit log line: {line!r}"
        assert "auth_failed" in line or "request_completed" in line, (
            f"the log line does not name the dropped event: {line!r}"
        )
        # The breadcrumb must not become the leak the audit service prevents.
        assert "reason" not in line and "Bearer" not in line and "eyJ" not in line, (
            f"the dropped-event log line leaked the detail payload: {line!r}"
        )
    finally:
        # Always restore, even on assertion failure — every later test that
        # reads audit rows depends on this.
        _compose("start", "audit")
        _wait_for_audit(http)


# ==========================================================================
# Session 2 — written ahead of the code, deselected by default.
# Run with: uv run pytest tests/ -m session2
# ==========================================================================

@pytest.mark.session2
def test_orchestrator_rejects_a_request_with_no_token(
    http: httpx.Client, session2_stack: None
) -> None:
    """The bypass demo (SPEC §7 step 4) curls this service directly. It has to
    validate for itself; nothing upstream vouched for the caller."""
    response = post_chat(http, authorization=None, base_url=ORCHESTRATOR_URL)
    assert_unauthorized(response, "an unauthenticated POST straight to the orchestrator")


@pytest.mark.session2
@pytest.mark.parametrize("server", sorted(MCP_SERVERS))
def test_mcp_server_rejects_a_request_with_no_token(
    http: httpx.Client, session2_stack: None, server: str
) -> None:
    response = mcp_initialize_request(http, MCP_SERVERS[server], token=None)
    assert_unauthorized(response, f"an unauthenticated MCP initialize against {server}")


@pytest.mark.session2
def test_orchestrator_rejects_an_expired_token(
    http: httpx.Client, session2_stack: None, mint: Callable[..., str]
) -> None:
    issued = int(time.time()) - TOKEN_TTL_SECONDS - 3600
    token = mint(claims={"iat": issued, "exp": issued + TOKEN_TTL_SECONDS})
    response = post_chat_with_token(http, token, base_url=ORCHESTRATOR_URL)
    assert_unauthorized(response, "an expired token at the orchestrator")


@pytest.mark.session2
@pytest.mark.parametrize("server", sorted(MCP_SERVERS))
def test_mcp_server_rejects_an_expired_token(
    http: httpx.Client, session2_stack: None, mint: Callable[..., str], server: str
) -> None:
    """Each MCP server checks `exp` itself. Six services, six independent
    verifications (SPEC §6) — no server trusts the hop before it."""
    issued = int(time.time()) - TOKEN_TTL_SECONDS - 3600
    token = mint(claims={"iat": issued, "exp": issued + TOKEN_TTL_SECONDS})
    response = mcp_initialize_request(http, MCP_SERVERS[server], token=token)
    assert_unauthorized(response, f"an expired token at {server}")


@pytest.mark.session2
def test_orchestrator_rejects_a_tampered_signature(
    http: httpx.Client, session2_stack: None, dana_token: str
) -> None:
    """A real, current token for a real persona, with one byte flipped.

    Claims that read correctly are not evidence of anything. The orchestrator
    has to do the maths itself, because the bypass demo (SPEC §7 step 4) reaches
    it with no gateway in front to have done it first.
    """
    tampered = mutate_signature(dana_token)
    assert tampered != dana_token, "the tamper helper did not change the token"
    response = post_chat_with_token(http, tampered, base_url=ORCHESTRATOR_URL)
    assert_unauthorized(response, "a token with a tampered signature at the orchestrator")


@pytest.mark.session2
@pytest.mark.parametrize("server", sorted(MCP_SERVERS))
def test_mcp_server_rejects_a_tampered_signature(
    http: httpx.Client, session2_stack: None, dana_token: str, server: str
) -> None:
    """Including mcp-labor, whose data is public.

    The data is public; the mechanism is not optional (SPEC §4.5). A server that
    skipped verification because its rows are harmless would break the claim
    that all six services validate independently.
    """
    tampered = mutate_signature(dana_token)
    assert tampered != dana_token, "the tamper helper did not change the token"
    response = mcp_initialize_request(http, MCP_SERVERS[server], token=tampered)
    assert_unauthorized(response, f"a token with a tampered signature at {server}")


@pytest.mark.session2
def test_orchestrator_rejects_a_token_for_a_different_audience(
    http: httpx.Client, session2_stack: None, mint: Callable[..., str]
) -> None:
    """Genuinely signed by identity-stub, issued for somewhere else.

    `aud` is what stops a token minted for a neighbouring system from being
    replayed here, and it is the check most easily lost when a service copies
    its verification call from another service and drops an argument.
    """
    token = mint(claims={"aud": "some-other-api"})
    response = post_chat_with_token(http, token, base_url=ORCHESTRATOR_URL)
    assert_unauthorized(
        response, f"a token with aud='some-other-api' instead of {AUDIENCE!r} at the orchestrator"
    )


@pytest.mark.session2
@pytest.mark.parametrize("server", sorted(MCP_SERVERS))
def test_mcp_server_rejects_a_token_for_a_different_audience(
    http: httpx.Client, session2_stack: None, mint: Callable[..., str], server: str
) -> None:
    token = mint(claims={"aud": "some-other-api"})
    response = mcp_initialize_request(http, MCP_SERVERS[server], token=token)
    assert_unauthorized(
        response, f"a token with aud='some-other-api' instead of {AUDIENCE!r} at {server}"
    )


@pytest.mark.session2
def test_orchestrator_rejects_a_token_from_a_different_issuer(
    http: httpx.Client, session2_stack: None, mint: Callable[..., str]
) -> None:
    """`iss` completes the set. SPEC §6 requires signature, iss, aud and exp to
    be checked by every service, and until now only the gateway was asked about
    `iss` — the other five were covered for the other three and taken on trust
    for this one. A shared helper is a reason to expect the check is there, not
    evidence that each service calls it with the issuer argument still attached.
    """
    token = mint(claims={"iss": "http://evil-idp.example.com"})
    response = post_chat_with_token(http, token, base_url=ORCHESTRATOR_URL)
    assert_unauthorized(
        response,
        f"a token with iss='http://evil-idp.example.com' instead of {ISSUER!r} at the orchestrator",
    )


@pytest.mark.session2
@pytest.mark.parametrize("server", sorted(MCP_SERVERS))
def test_mcp_server_rejects_a_token_from_a_different_issuer(
    http: httpx.Client, session2_stack: None, mint: Callable[..., str], server: str
) -> None:
    token = mint(claims={"iss": "http://evil-idp.example.com"})
    response = mcp_initialize_request(http, MCP_SERVERS[server], token=token)
    assert_unauthorized(
        response, f"a token with iss='http://evil-idp.example.com' instead of {ISSUER!r} at {server}"
    )


# --------------------------------------------------------------------------
# Scope types the auth middleware will not serve.
#
# The middleware wraps the app FastMCP built, so it sees every ASGI scope before
# any route matches. It used to let all non-`http` scopes through, because
# `lifespan` has to reach the session manager — which meant any scope type that
# was not `http` was handed to the application with no token checked. No
# websocket route exists on these servers, so it was never exploitable; it was a
# trapdoor left open for whoever adds one.
#
# It is now an allowlist: `lifespan` and `GET /healthz` pass, `http` is
# validated, everything else is closed without dispatching. This test uses a
# VALID token on purpose — the refusal must come from the connection type, not
# from authentication, or it would still pass once the trapdoor reopened.
# --------------------------------------------------------------------------


def websocket_handshake_status(base_url: str, token: str) -> int:
    """Attempt a WebSocket upgrade over a raw socket, returning the HTTP status.

    Hand-framed because the test workspace carries no websocket client, and
    because an attacker has none of a library's scruples about which endpoints
    are meant to be upgraded. A refusal before `accept` reaches the client as an
    ordinary HTTP response; 101 would mean the upgrade completed.
    """
    url = httpx.URL(base_url)
    host, port = url.host, url.port or 80
    key = base64.b64encode(b"0123456789abcdef").decode()
    request = (
        f"GET {MCP_PATH} HTTP/1.1\r\n".encode()
        + f"Host: {host}:{port}\r\n".encode()
        + b"Upgrade: websocket\r\n"
        + b"Connection: Upgrade\r\n"
        + f"Sec-WebSocket-Key: {key}\r\n".encode()
        + b"Sec-WebSocket-Version: 13\r\n"
        + f"Authorization: Bearer {token}\r\n".encode()
        + b"\r\n"
    )

    with socket.create_connection((host, port), timeout=10.0) as sock:
        sock.sendall(request)
        received = b""
        while b"\r\n" not in received:
            chunk = sock.recv(4096)
            if not chunk:
                break
            received += chunk

    if not received:
        # The server hung up without replying. That is a refusal too.
        return 0
    status_line = received.split(b"\r\n", 1)[0].decode("latin-1")
    parts = status_line.split()
    assert len(parts) >= 2 and parts[0].startswith("HTTP/"), (
        f"no parseable status line from a websocket upgrade attempt: {status_line!r}"
    )
    return int(parts[1])


@pytest.mark.session2
@pytest.mark.parametrize("server", sorted(MCP_SERVERS))
def test_websocket_upgrade_is_refused_without_reaching_the_server(
    http: httpx.Client, session2_stack: None, token_for: Callable[[str], str], server: str
) -> None:
    """A websocket must be closed BY THE MIDDLEWARE, even carrying a good token.

    The status code alone cannot prove this and must not be trusted to. Starlette
    also closes a websocket that matches no route, and uvicorn reports both
    closes as HTTP 403 — so a test asserting only "not 101" passes just as well
    against the trapdoor it is supposed to guard. Verified by reverting the
    middleware and watching the status-only assertion stay green.

    The audit row is what distinguishes them. Only the middleware writes one, and
    it can only write one if it handled the connection itself instead of handing
    it to the app.
    """
    since = utcnow() - timedelta(seconds=2)
    status = websocket_handshake_status(MCP_SERVERS[server], token_for("dana"))

    assert status != 101, (
        f"{server} completed a WebSocket upgrade on {MCP_PATH}. A completed upgrade means "
        "the connection reached the application."
    )
    assert status in {0, 400, 403}, (
        f"{server} answered a websocket upgrade with HTTP {status}. Expected it closed "
        "before accept (uvicorn reports that as 403), not served."
    )

    event = wait_for_event(
        http,
        lambda row: (
            row.get("service") == server
            and row.get("event") == "auth_failed"
            and "websocket" in str(row.get("detail", {}).get("reason", "")).lower()
        ),
        since=since,
    )
    assert event is not None, (
        f"{server} refused the upgrade but wrote no audit row naming the connection type. "
        "That means the middleware passed the websocket scope to the application and "
        "something downstream closed it — the connection reached code that never checked "
        "a token. The middleware must close every scope type it cannot authenticate."
    )


# --------------------------------------------------------------------------
# Session identity. A tool must see the caller on THIS request, and no other.
#
# The bug these guard is not hypothetical and it does not announce itself. In
# FastMCP's default stateful mode, every tool runs inside the task that the
# *initialize* request created, so a ContextVar set by per-request middleware is
# invisible to the tool — it goes on reading the identity of whoever opened the
# session. Two people, one open session, and every call executes as the first
# one. That is a confused deputy reached through the back door, and it would
# make every refusal in this file decorative.
#
# The servers avoid it two ways at once: stateless_http=True, and claims carried
# on the per-request ASGI scope rather than in a ContextVar. These tests assert
# the observable behaviour, so they hold whichever mechanism is in place — and
# they fail if either one is quietly removed.
# --------------------------------------------------------------------------


@pytest.mark.session2
def test_a_tool_call_runs_as_the_token_on_that_request_not_the_session(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """Open the session as dana (advisor), drive the tool call as kim (dean).

    kim must be refused for lacking the advisor role. Dana's advisee roster
    coming back would mean the tool read the identity that opened the session
    instead of the identity on the request in front of it.
    """
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("dana")) as session:
        response = session.call_tool_as("get_my_advisees", {}, token=token_for("kim"))

    assert response.status_code < 400, (
        f"expected the call to be answered, got HTTP {response.status_code}: {response.text[:200]}"
    )
    payload = decode_jsonrpc(response)
    body = json.dumps(payload)
    result = payload.get("result", {})
    refused = "error" in payload or bool(result.get("isError"))
    assert refused, (
        "kim holds only the dean role and must be refused get_my_advisees, even on a "
        f"session dana opened. Got: {body[:400]}"
    )
    assert "advisor" in body.lower(), (
        f"the refusal must name the advisor role kim is missing. Got: {body[:400]}"
    )
    assert "S-" not in body, (
        "dana's advisees came back for kim: the tool observed the identity that opened "
        f"the session, not the one on this request. Got: {body[:400]}"
    )


@pytest.mark.session2
def test_dropping_the_token_mid_session_is_rejected(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """The negative control for the test above.

    An open session must confer nothing. Strip the Authorization header from a
    follow-up call and the server has to answer 401 — if it serves the request
    on the strength of an earlier one, authentication has become a property of
    the connection rather than of the request, and every per-request check in
    this file is measuring the wrong thing.
    """
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("dana")) as session:
        response = session.call_tool_as("get_my_advisees", {}, token=None)

    assert_unauthorized(response, "a tools/call with no token on a session dana opened")
    assert "S-" not in response.text, (
        f"the 401 body leaked student data: {response.text[:300]}"
    )


@pytest.fixture(scope="session")
def dana_advisee_ids(session2_stack: None, token_for: Callable[[str], str]) -> list[str]:
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("dana")) as session:
        result = session.call_tool("get_my_advisees", {})
    assert not result.refused, f"dana holds the advisor role and must be served: {result.text[:300]}"
    ids = student_ids_in(result.text)
    assert len(ids) >= 2, (
        f"expected dana to have a block of advisees, found {ids}; check scripts/seed.py"
    )
    return ids


@pytest.mark.session2
def test_adjunct_is_refused_the_advisee_roster(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """The money shot: pat's token is valid, pat reaches the tool server
    directly, and the tool server still says no (SPEC §7 step 4)."""
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("pat")) as session:
        result = session.call_tool("get_my_advisees", {})
    assert result.refused, (
        f"pat holds only the adjunct role and must be refused get_my_advisees. Got: {result.text[:300]}"
    )
    assert "advisor" in result.text.lower(), (
        f"the refusal must name the advisor role so the model can relay it. Got: {result.text[:300]}"
    )


@pytest.mark.session2
def test_advisor_is_refused_another_advisors_student(
    session2_stack: None, token_for: Callable[[str], str], dana_advisee_ids: list[str]
) -> None:
    other_students_id = pick_id_outside(dana_advisee_ids)
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("dana")) as session:
        result = session.call_tool("get_student_summary", {"student_id": other_students_id})
    assert result.refused, (
        f"{other_students_id} is not one of dana's advisees and must be refused. "
        f"Got: {result.text[:300]}"
    )
    assert other_students_id in result.text, (
        f"the refusal must name the student asked about ({other_students_id}). Got: {result.text[:300]}"
    )
    assert "not among your assigned advisees" in result.text, (
        f"the refusal must name the boundary, not just deny. Got: {result.text[:300]}"
    )


@pytest.mark.session2
def test_dean_asking_for_an_individual_record_gets_the_aggregates_line(
    session2_stack: None, token_for: Callable[[str], str], dana_advisee_ids: list[str]
) -> None:
    """SPEC §4.4 fixes this sentence word for word — it is the RBAC demo."""
    student_id = dana_advisee_ids[0]
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("kim")) as session:
        result = session.call_tool("get_student_summary", {"student_id": student_id})
    assert result.refused, (
        f"kim is a dean and must be refused an individual record. Got: {result.text[:300]}"
    )
    assert DEAN_INDIVIDUAL_RECORD_REFUSAL in result.text, (
        "the dean refusal must read exactly:\n"
        f"  {DEAN_INDIVIDUAL_RECORD_REFUSAL}\n"
        f"got:\n  {result.text[:300]}"
    )


@pytest.mark.session2
def test_faculty_is_refused_a_section_they_do_not_teach(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """noor teaches CYB-310-A and CYB-210-A. BUS-201-A belongs to someone else.
    SPEC §4.6 fixes this sentence word for word."""
    with mcp_session(MCP_SERVERS["mcp-canvas"], token_for("noor")) as session:
        result = session.call_tool("get_section_engagement", {"section_id": NOOR_FOREIGN_SECTION})
    assert result.refused, (
        f"{NOOR_FOREIGN_SECTION} is not noor's section and must be refused. Got: {result.text[:300]}"
    )
    assert FOREIGN_SECTION_REFUSAL in result.text, (
        "the cross-section refusal must read exactly:\n"
        f"  {FOREIGN_SECTION_REFUSAL}\n"
        f"got:\n  {result.text[:300]}"
    )


@pytest.mark.session2
def test_dean_may_read_the_same_section_the_faculty_member_could_not(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """The asymmetry, proven at the tool layer: same call, same server, same
    second — the answer depends only on the role in the caller's own token."""
    with mcp_session(MCP_SERVERS["mcp-canvas"], token_for("kim")) as session:
        result = session.call_tool("get_section_engagement", {"section_id": NOOR_FOREIGN_SECTION})
    assert not result.refused, (
        f"kim is a dean and may read any section, including {NOOR_FOREIGN_SECTION}. "
        f"Got: {result.text[:300]}"
    )
    assert result.text.strip(), f"the dean's section view came back empty: {result.raw!r}"


# --------------------------------------------------------------------------
# A refusal in the audit trail must always mean somebody was told no.
#
# All four MCP servers now sort a tool call into the same three tiers, by
# exception TYPE and never by reading a message: a refusal the rules raised on
# purpose is `refused`; a caller who named something that does not exist is
# `error`, with the argument named; a fault in the server is `error` recorded
# as a bare class name, and the caller gets one fixed sentence. The viewer
# paints `refused` amber, so this distinction is the only thing keeping a
# mistyped code out of the row of genuine RBAC refusals it would otherwise sit
# in during demo moment 9.
#
# The two tests below run as a pair and only mean something together. The first
# pins the bad-argument tier. The second is the negative control: `error`
# existing must not have eaten `refused`. Both assert on `decision` and on a
# reason PREFIX, never on the whole message, so they pin the contract rather
# than the wording.
#
# Every server appears in at least one of the two. Two of the eight cells do
# not exist, by design rather than by omission, and neither is worth
# manufacturing:
#
#   * mcp-colleague has no reachable bad argument. `require_assignment` runs
#     before the register is read, so an id belonging to nobody is refused as
#     "not among your assigned advisees" rather than confirmed absent — the
#     tools deliberately do not double as a way to probe which ids exist.
#     `UnknownStudent` is left for the genuine fault it describes.
#   * mcp-labor refuses nobody. SPEC §4.5 gives its data to every authenticated
#     role; the mechanism is identical and the answer is always yes.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolCase:
    """One tool call, and the audit row it is required to produce."""

    server: str
    persona: str
    tool: str
    args: dict[str, Any]
    reason_prefix: str


BAD_ARGUMENT_CASES = [
    ToolCase("mcp-kuali", "kim", "get_course_outcomes",
             {"program_code": "ZZZ-XX"}, "unknown program code"),
    ToolCase("mcp-canvas", "kim", "get_section_engagement",
             {"section_id": "ZZZ-999-Z"}, "unknown section id"),
    ToolCase("mcp-labor", "pat", "get_occupation",
             {"soc_code": "99-9999"}, "unknown SOC code"),
]

ROLE_REFUSAL_CASES = [
    ToolCase("mcp-kuali", "pat", "get_course_outcomes",
             {"program_code": "CYB-BS"}, "get_course_outcomes requires"),
    ToolCase("mcp-canvas", "pat", "get_section_engagement",
             {"section_id": "CYB-310-A"}, "get_section_engagement requires"),
    ToolCase("mcp-colleague", "pat", "get_my_advisees",
             {}, "get_my_advisees requires"),
]


def expected_args_hash(args: dict[str, Any]) -> str:
    """The correlation key the servers write, derived here independently.

    Two tests in this file call the same tool on the same server as the same
    persona a second apart, so the tool name alone does not identify a row.
    Re-deriving the digest rather than importing it also pins the contract: the
    audit trail's `args_hash` is a stable digest of the sorted arguments, and a
    change to how it is computed should fail a test.
    """
    payload = json.dumps(args, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def tool_call_row(
    client: httpx.Client, case: ToolCase, since: datetime
) -> dict[str, Any]:
    """The tool_call row this case just caused, or a clear failure."""
    args_hash = expected_args_hash(case.args)
    row = wait_for_event(
        client,
        lambda event: (
            event.get("service") == case.server
            and event.get("event") == "tool_call"
            and event.get("sub") == case.persona
            and (event.get("detail") or {}).get("tool") == case.tool
            and (event.get("detail") or {}).get("args_hash") == args_hash
        ),
        since=since,
    )
    assert row is not None, (
        f"{case.server} wrote no tool_call row for {case.persona} calling "
        f"{case.tool}. Every call is audited, allowed or refused."
    )
    return row


@pytest.mark.session2
@pytest.mark.parametrize("case", BAD_ARGUMENT_CASES, ids=lambda c: c.server)
def test_a_bad_argument_audits_as_an_error_not_a_refusal(
    session2_stack: None, http: httpx.Client, token_for: Callable[[str], str],
    case: ToolCase,
) -> None:
    """Each persona here holds the role the tool wants, so the role gate lets
    them through and the tool then fails on the argument. That is the model
    mistyping a code, not the university telling anybody no, and the trail has
    to say which."""
    since = utcnow() - timedelta(seconds=2)
    with mcp_session(MCP_SERVERS[case.server], token_for(case.persona)) as session:
        result = session.call_tool(case.tool, case.args)

    assert result.refused, (
        f"{case.server}: a bad argument must come back as a tool error. "
        f"Got: {result.text[:300]}"
    )
    assert case.reason_prefix in result.text, (
        f"{case.server}: the tool reply must name the bad argument, not read like "
        f"a refusal. Got: {result.text[:300]}"
    )

    detail = tool_call_row(http, case, since).get("detail") or {}
    assert detail.get("decision") == "error", (
        f"{case.server}: a bad argument must audit as decision 'error'. Auditing "
        "it as 'refused' paints it amber in the viewer beside the real RBAC "
        "refusals, and its honest explanation is 'the caller named something that "
        f"does not exist'. Got: {detail!r}"
    )
    assert str(detail.get("reason", "")).startswith(case.reason_prefix), (
        f"{case.server}: the audit reason must begin {case.reason_prefix!r}, not "
        f"an exception class name. Got: {detail.get('reason')!r}"
    )


@pytest.mark.session2
@pytest.mark.parametrize("case", ROLE_REFUSAL_CASES, ids=lambda c: c.server)
def test_a_role_refusal_still_audits_as_refused(
    session2_stack: None, http: httpx.Client, token_for: Callable[[str], str],
    case: ToolCase,
) -> None:
    """The control for the test above. pat is an adjunct and holds none of the
    roles these tools want, and the role gate runs before the argument is ever
    looked at — so each of these is a refusal and must still be recorded as
    one."""
    since = utcnow() - timedelta(seconds=2)
    with mcp_session(MCP_SERVERS[case.server], token_for(case.persona)) as session:
        result = session.call_tool(case.tool, case.args)

    assert result.refused, (
        f"{case.server}: pat holds none of the roles {case.tool} wants and must be "
        f"refused. Got: {result.text[:300]}"
    )

    detail = tool_call_row(http, case, since).get("detail") or {}
    assert detail.get("decision") == "refused", (
        f"{case.server}: a role refusal must still audit as decision 'refused'. "
        f"Introducing 'error' must not have swallowed the refusals. Got: {detail!r}"
    )
    assert str(detail.get("reason", "")).startswith(case.reason_prefix), (
        f"{case.server}: a refusal's audit reason is the message the caller was "
        f"given, so it names the tool and the role it wanted. "
        f"Got: {detail.get('reason')!r}"
    )


@pytest.mark.session2
def test_every_mcp_server_tells_the_caller_the_same_thing_when_it_faults() -> None:
    """The fixed sentence a fault returns is the one thing all four servers hand
    to the model, so it must not drift between them. Four copies is the standing
    trade this repo makes for readable, self-contained servers; a test is what
    makes the copies safe."""
    sentences = {}
    for server in ("mcp-colleague", "mcp-canvas", "mcp-kuali", "mcp-labor"):
        source = (REPO_ROOT / "services" / server / "rules.py").read_text()
        namespace: dict[str, Any] = {}
        for line in source.splitlines():
            if line.startswith("INTERNAL_ERROR"):
                exec(line, namespace)  # noqa: S102 — a literal assignment we just matched
        assert "INTERNAL_ERROR" in namespace, (
            f"services/{server}/rules.py defines no INTERNAL_ERROR. All four servers "
            "classify a fault the same way and answer it with the same sentence."
        )
        sentences[server] = namespace["INTERNAL_ERROR"]

    assert len(set(sentences.values())) == 1, (
        f"the four servers' INTERNAL_ERROR sentences have drifted: {sentences!r}"
    )
