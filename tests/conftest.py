"""Fixtures for the harness-poc test suite (SPEC §6).

Everything here talks to the live compose stack over published localhost ports.
Nothing here mocks, patches, or weakens token validation. The tests mint real
tokens from identity-stub, and mint deliberately-bad ones by signing with
identity-stub's own RSA private key from the ./data bind mount. See the header
comment of tests/test_auth.py for why that signing technique is POC-only and
must not be carried into production.
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

# --------------------------------------------------------------------------
# Where things live. Env overrides exist so the suite can be pointed at a
# remote stack; the defaults are the published compose ports on localhost.
# --------------------------------------------------------------------------

IDENTITY_URL: str = os.environ.get("HARNESS_IDENTITY_URL", "http://localhost:8001")
GATEWAY_URL: str = os.environ.get("HARNESS_GATEWAY_URL", "http://localhost:8000")
AUDIT_URL: str = os.environ.get("HARNESS_AUDIT_URL", "http://localhost:8030")
ORCHESTRATOR_URL: str = os.environ.get("HARNESS_ORCHESTRATOR_URL", "http://localhost:8010")

MCP_SERVERS: dict[str, str] = {
    "mcp-colleague": os.environ.get("HARNESS_MCP_COLLEAGUE_URL", "http://localhost:8021"),
    "mcp-labor": os.environ.get("HARNESS_MCP_LABOR_URL", "http://localhost:8022"),
    "mcp-canvas": os.environ.get("HARNESS_MCP_CANVAS_URL", "http://localhost:8023"),
    "mcp-kuali": os.environ.get("HARNESS_MCP_KUALI_URL", "http://localhost:8024"),
}

SESSION1_SERVICES: dict[str, str] = {
    "identity-stub": IDENTITY_URL,
    "gateway": GATEWAY_URL,
    "audit": AUDIT_URL,
}

# The issuer stays the in-container hostname even though the tests reach
# identity-stub on localhost: services compare `iss` as an opaque string.
ISSUER: str = os.environ.get("HARNESS_JWT_ISSUER", "http://identity-stub:8001")
AUDIENCE: str = os.environ.get("JWT_AUDIENCE", "harness-poc")
TOKEN_TTL_SECONDS: int = 8 * 60 * 60  # SPEC §3: exp = iat + 8h

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
PRIVATE_KEY_PATH: Path = REPO_ROOT / "data" / "jwt_private.pem"

# SPEC §3 / config/personas.yaml. All passwords are "demo".
PERSONA_PASSWORD: str = "demo"
PERSONA_ROLES: dict[str, list[str]] = {
    "dana": ["advisor"],
    "kim": ["dean"],
    "noor": ["faculty"],
    "pat": ["adjunct"],
    "sam": ["advisor", "dean"],
}
PERSONA_NAMES: dict[str, str] = {
    "dana": "Dana Whitfield",
    "kim": "Kim Okafor",
    "noor": "Noor Haddad",
    "pat": "Pat Reyes",
    "sam": "Sam Lindqvist",
}

STACK_HINT: str = (
    "This suite runs against the LIVE compose stack — there is no mocked mode "
    "and there will not be one. Start it first:\n"
    "    docker compose up --build\n"
    "    uv run scripts/seed.py\n"
)

# FastMCP streamable HTTP defaults. If the servers mount elsewhere, change
# these two constants rather than each test.
MCP_PATH: str = "/mcp"
MCP_PROTOCOL_VERSION: str = "2025-06-18"


# --------------------------------------------------------------------------
# Stack reachability — fail fast, with a message that says what to do.
# --------------------------------------------------------------------------


def _require_reachable(client: httpx.Client, name: str, base_url: str, *, healthz: bool) -> None:
    """Fail the whole session if `name` is not answering on `base_url`."""
    url = f"{base_url}/healthz" if healthz else base_url
    try:
        response = client.get(url, timeout=5.0)
    except httpx.HTTPError as exc:
        pytest.fail(f"{name} is not reachable at {base_url} ({exc}).\n\n{STACK_HINT}", pytrace=False)
    if healthz and response.status_code != 200:
        pytest.fail(
            f"{name} answered GET {url} with {response.status_code}, expected 200.\n\n{STACK_HINT}",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def http() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def stack_up(http: httpx.Client) -> None:
    """Session 1 services must be live before any test runs."""
    for name, base_url in SESSION1_SERVICES.items():
        _require_reachable(http, name, base_url, healthz=True)


@pytest.fixture(scope="session")
def session2_stack(http: httpx.Client) -> None:
    """Session 2 services. Requested only by @pytest.mark.session2 tests.

    Any HTTP status counts as reachable — an MCP server answering 401 or 406 to
    a bare GET is up. Only a connection failure fails the session.
    """
    for name, base_url in {"orchestrator": ORCHESTRATOR_URL, **MCP_SERVERS}.items():
        _require_reachable(http, name, base_url, healthz=False)


# --------------------------------------------------------------------------
# Keys. The private key is identity-stub's own, read from the host side of the
# ./data bind mount. POC-only — see the test_auth.py header.
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def private_key() -> RSAPrivateKey:
    if not PRIVATE_KEY_PATH.is_file():
        pytest.fail(
            f"No RSA private key at {PRIVATE_KEY_PATH}.\n"
            "identity-stub generates the keypair into the ./data bind mount on first "
            "boot, and these tests read the host side of that mount so they can sign "
            "correctly-signed-but-wrong tokens (expired, wrong aud, wrong iss, "
            "missing claims). Without it every negative case would collapse into "
            '"bad signature" and prove much less.\n\n' + STACK_HINT,
            pytrace=False,
        )
    key = serialization.load_pem_private_key(PRIVATE_KEY_PATH.read_bytes(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        pytest.fail(f"{PRIVATE_KEY_PATH} is not an RSA private key (SPEC §3 requires RS256).", pytrace=False)
    return key


@pytest.fixture(scope="session")
def public_key_pem(private_key: RSAPrivateKey) -> bytes:
    """identity-stub's public key in PEM form — the HMAC secret for the
    algorithm-confusion attack, which is exactly the point of that attack."""
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


@pytest.fixture(scope="session")
def foreign_private_key() -> RSAPrivateKey:
    """A throwaway key the harness has never seen. Used for exactly one test:
    the foreign-signature case, which must fail on the signature itself."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(http: httpx.Client) -> dict[str, Any]:
    response = http.get(f"{IDENTITY_URL}/jwks.json")
    assert response.status_code == 200, (
        f"GET {IDENTITY_URL}/jwks.json returned {response.status_code}; "
        "every service needs this document to verify signatures."
    )
    document = response.json()
    assert document.get("keys"), f"jwks.json published no keys: {document!r}"
    return document


@pytest.fixture(scope="session")
def signing_kid(jwks: dict[str, Any]) -> str:
    """The `kid` of the published key.

    Bad tokens carry the REAL kid on purpose: the server then looks up the right
    key, the signature verifies, and the request fails on the claim under test
    instead of on an unknown key id.
    """
    return str(jwks["keys"][0]["kid"])


def rsa_key_from_jwks(jwks_document: dict[str, Any], kid: str) -> Any:
    """Rebuild a public key object from the published JWKS entry with this kid."""
    for key in jwks_document["keys"]:
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    raise AssertionError(f"kid {kid!r} is not published in jwks.json (kids: {[k.get('kid') for k in jwks_document['keys']]})")


# --------------------------------------------------------------------------
# Minting tokens: real ones from identity-stub, bad ones signed here.
# --------------------------------------------------------------------------


def base_claims(persona: str = "dana", *, ttl_seconds: int = TOKEN_TTL_SECONDS) -> dict[str, Any]:
    """A claim set that should pass every check. Tests break exactly one thing."""
    now = int(time.time())
    return {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": persona,
        "name": PERSONA_NAMES[persona],
        "roles": list(PERSONA_ROLES[persona]),
        "iat": now,
        "exp": now + ttl_seconds,
    }


@pytest.fixture(scope="session")
def mint(private_key: RSAPrivateKey, signing_kid: str) -> Callable[..., str]:
    """Sign a token with identity-stub's own key.

    mint()                                  -> a token that should be accepted
    mint(claims={"aud": "other-api"})        -> overrides on top of the base set
    mint(drop=["exp"])                       -> a required claim removed
    mint(key=foreign_key)                    -> signed by a key nobody trusts
    """

    def _mint(
        *,
        claims: dict[str, Any] | None = None,
        drop: Sequence[str] = (),
        persona: str = "dana",
        key: RSAPrivateKey | None = None,
        kid: str | None = None,
    ) -> str:
        payload = base_claims(persona)
        payload.update(claims or {})
        for name in drop:
            payload.pop(name, None)
        return jwt.encode(
            payload,
            key=key or private_key,
            algorithm="RS256",
            headers={"kid": kid or signing_kid},
        )

    return _mint


def request_token(client: httpx.Client, persona: str, password: str = PERSONA_PASSWORD) -> httpx.Response:
    return client.post(f"{IDENTITY_URL}/token", json={"persona": persona, "password": password})


@pytest.fixture(scope="session")
def token_for(http: httpx.Client) -> Callable[[str], str]:
    """A real token from identity-stub, cached per persona for the session."""
    cache: dict[str, str] = {}

    def _token(persona: str) -> str:
        if persona not in cache:
            response = request_token(http, persona)
            assert response.status_code == 200, (
                f"identity-stub would not mint a token for {persona}: "
                f"{response.status_code} {response.text[:200]}"
            )
            access_token = response.json().get("access_token")
            assert isinstance(access_token, str) and access_token, (
                f"POST /token for {persona} returned no access_token: {response.text[:200]}"
            )
            cache[persona] = access_token
        return cache[persona]

    return _token


@pytest.fixture
def dana_token(token_for: Callable[[str], str]) -> str:
    return token_for("dana")


# --------------------------------------------------------------------------
# Gateway helpers.
# --------------------------------------------------------------------------


def post_chat(
    client: httpx.Client,
    *,
    authorization: str | None,
    message: str = "hello",
    base_url: str = GATEWAY_URL,
) -> httpx.Response:
    """POST /chat with an arbitrary (or absent) Authorization header."""
    headers: dict[str, str] = {} if authorization is None else {"Authorization": authorization}
    return client.post(
        f"{base_url}/chat",
        json={"message": message, "history": []},
        headers=headers,
    )


def post_chat_with_token(
    client: httpx.Client,
    token: str,
    message: str = "hello",
    *,
    base_url: str = GATEWAY_URL,
) -> httpx.Response:
    return post_chat(client, authorization=f"Bearer {token}", message=message, base_url=base_url)


def raw_chat_status(authorization: str, *, base_url: str = GATEWAY_URL) -> int:
    """POST /chat over a hand-framed socket, returning the status code.

    Some Authorization values cannot be sent with a conforming client at all:
    RFC 9110 forbids trailing whitespace in a field value, so httpx raises
    LocalProtocolError rather than putting `Bearer ` on the wire. An attacker
    writes bytes to a socket and has no such scruples, so neither do we here.

    This is the only place in the suite that bypasses httpx, and it bypasses it
    to make the test stricter, never to make one pass.
    """
    url = httpx.URL(base_url)
    host = url.host
    port = url.port or 80
    body = b'{"message":"raw socket probe","history":[]}'
    request = (
        b"POST /chat HTTP/1.1\r\n"
        + f"Host: {host}:{port}\r\n".encode()
        + b"Content-Type: application/json\r\n"
        + f"Authorization: {authorization}\r\n".encode()
        + f"Content-Length: {len(body)}\r\n".encode()
        + b"Connection: close\r\n\r\n"
        + body
    )

    with socket.create_connection((host, port), timeout=10.0) as sock:
        sock.sendall(request)
        received = b""
        while b"\r\n" not in received:
            chunk = sock.recv(4096)
            if not chunk:
                break
            received += chunk

    status_line = received.split(b"\r\n", 1)[0].decode("latin-1")
    parts = status_line.split()
    assert len(parts) >= 2 and parts[0].startswith("HTTP/"), (
        f"gateway returned no parseable status line for Authorization={authorization!r}: "
        f"{status_line!r}"
    )
    return int(parts[1])


# --------------------------------------------------------------------------
# Audit helpers. audit_event is fire-and-forget, so reads poll.
# --------------------------------------------------------------------------


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str) -> datetime:
    """Parse an audit row timestamp. ISO-8601; a naive value is read as UTC."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_events(client: httpx.Client, limit: int = 100) -> list[dict[str, Any]]:
    response = client.get(f"{AUDIT_URL}/events", params={"limit": limit})
    assert response.status_code == 200, (
        f"GET {AUDIT_URL}/events returned {response.status_code}: {response.text[:200]}"
    )
    events = response.json()
    assert isinstance(events, list), f"GET /events must return a JSON array, got {type(events).__name__}"
    return events


def wait_for_event(
    client: httpx.Client,
    predicate: Callable[[dict[str, Any]], bool],
    *,
    since: datetime,
    timeout: float = 10.0,
    limit: int = 200,
) -> dict[str, Any] | None:
    """Poll GET /events until a row at or after `since` satisfies `predicate`.

    Returns the row, or None if it never showed up. Audit writes are
    fire-and-forget (SPEC §2), so a short retry loop is the honest read.
    """
    deadline = time.monotonic() + timeout
    while True:
        for event in fetch_events(client, limit):
            ts = event.get("ts")
            if not isinstance(ts, str):
                continue
            try:
                when = parse_ts(ts)
            except ValueError:
                continue
            if when >= since and predicate(event):
                return event
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.25)


def walk_values(node: Any) -> Iterator[str]:
    """Every string value anywhere inside a decoded JSON structure."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from walk_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_values(value)


def walk_keys(node: Any) -> Iterator[str]:
    """Every dict key anywhere inside a decoded JSON structure."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from walk_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_keys(value)


# --------------------------------------------------------------------------
# A minimal MCP streamable-HTTP client, built on httpx.
#
# The test workspace deliberately depends on nothing but pytest, httpx, pyjwt
# and cryptography, so the Session 2 tests speak JSON-RPC over streamable HTTP
# directly instead of pulling in the MCP SDK. Small on purpose.
# --------------------------------------------------------------------------

INITIALIZE_PARAMS: dict[str, Any] = {
    "protocolVersion": MCP_PROTOCOL_VERSION,
    "capabilities": {},
    "clientInfo": {"name": "harness-poc-auth-tests", "version": "0.1.0"},
}


def mcp_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def mcp_initialize_request(
    client: httpx.Client, base_url: str, *, token: str | None
) -> httpx.Response:
    """A bare initialize POST. Used by the no-token and bad-token tests, which
    must be rejected by the server's middleware before any MCP work happens."""
    return client.post(
        f"{base_url}{MCP_PATH}",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": INITIALIZE_PARAMS},
        headers=mcp_headers(token),
    )


def _decode_jsonrpc(response: httpx.Response) -> dict[str, Any]:
    """Streamable HTTP answers with either a JSON body or an SSE stream."""
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        for line in response.text.splitlines():
            if line.startswith("data:"):
                payload = json.loads(line[len("data:") :].strip())
                if isinstance(payload, dict) and ("result" in payload or "error" in payload):
                    return payload
        raise AssertionError(f"no JSON-RPC payload in SSE response: {response.text[:300]!r}")
    return response.json()


@dataclass(frozen=True)
class ToolResult:
    """What an MCP tool call came back with.

    `refused` is true for a JSON-RPC error and for a result flagged isError —
    an authorization refusal may legitimately arrive either way, and both are
    a refusal as far as the demo claim is concerned.
    """

    refused: bool
    text: str
    raw: dict[str, Any]


class MCPSession:
    """One authenticated MCP session against one server."""

    def __init__(self, base_url: str, token: str, client: httpx.Client) -> None:
        self.base_url = base_url
        self.url = f"{base_url}{MCP_PATH}"
        self._client = client
        self._token = token
        self._session_id: str | None = None
        self._next_id = 0

    def _headers(self) -> dict[str, str]:
        headers = mcp_headers(self._token)
        if self._session_id is not None:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        response = self._client.post(
            self.url,
            json={"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params},
            headers=self._headers(),
        )
        assert response.status_code < 400, (
            f"{method} on {self.url} returned HTTP {response.status_code}: {response.text[:300]}"
        )
        return _decode_jsonrpc(response)

    def open(self) -> None:
        self._next_id += 1
        response = self._client.post(
            self.url,
            json={"jsonrpc": "2.0", "id": self._next_id, "method": "initialize", "params": INITIALIZE_PARAMS},
            headers=self._headers(),
        )
        assert response.status_code < 400, (
            f"initialize on {self.url} returned HTTP {response.status_code}: {response.text[:300]}"
        )
        self._session_id = response.headers.get("mcp-session-id")
        self._client.post(
            self.url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=self._headers(),
        )

    def close(self) -> None:
        if self._session_id is None:
            return
        try:
            self._client.delete(self.url, headers=self._headers())
        except httpx.HTTPError:
            pass  # session teardown is best-effort; the test's verdict is already in

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        payload = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in payload:
            error = payload["error"]
            return ToolResult(refused=True, text=str(error.get("message", "")) + " " + json.dumps(error.get("data", "")), raw=payload)
        result = payload.get("result", {})
        chunks = [
            block.get("text", "")
            for block in result.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if "structuredContent" in result:
            chunks.append(json.dumps(result["structuredContent"]))
        return ToolResult(refused=bool(result.get("isError")), text="\n".join(chunks), raw=payload)


@contextmanager
def mcp_session(base_url: str, token: str) -> Iterator[MCPSession]:
    with httpx.Client(timeout=30.0) as client:
        session = MCPSession(base_url, token, client)
        session.open()
        try:
            yield session
        finally:
            session.close()


STUDENT_ID_PATTERN = re.compile(r"\bS-\d+\b")


def student_ids_in(text: str) -> list[str]:
    """Student ids as they appear in seeded data (SPEC §4.4 uses S-1042)."""
    return sorted(set(STUDENT_ID_PATTERN.findall(text)))


def pick_id_outside(known_ids: Sequence[str]) -> str:
    """A student id in the same numeric neighbourhood as `known_ids` but not in it.

    Staying inside the min/max of the caller's own advisees keeps the pick on a
    seeded student, so the refusal we assert on is the authorization boundary
    and not a "no such student" answer.
    """
    assert known_ids, "cannot pick a neighbouring id without at least one known id"
    prefix, sample_digits = known_ids[0].split("-", 1)
    width = len(sample_digits)
    numbers = sorted(int(student_id.split("-", 1)[1]) for student_id in known_ids)
    for candidate_number in range(numbers[0], numbers[-1] + 1):
        candidate = f"{prefix}-{str(candidate_number).zfill(width)}"
        if candidate not in set(known_ids):
            return candidate
    raise AssertionError(
        f"every id between {numbers[0]} and {numbers[-1]} belongs to this advisor; "
        "adjust scripts/seed.py so the advisee block is not contiguous"
    )
