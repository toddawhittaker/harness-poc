"""Per-request Bearer validation for an MCP server (SPEC §4.4).

DUPLICATED, DELIBERATELY. This file is copied byte-for-byte into all four
mcp-* services. The obvious move is to lift it into libs/harness_auth, and the
session brief allowed that under ~40 lines — but harness_auth is fixed, and a
fifth shared module for thirty lines buys less than it costs to read.

The duplication is safe because, and only because, the negative-auth tests are
parametrized across all four servers — drift in any stamp fails the suite. If
that parametrization is ever narrowed, this decision must be revisited.

WHY THE CLAIMS LIVE IN THE ASGI SCOPE AND NOT IN A CONTEXTVAR
-------------------------------------------------------------
A ContextVar set here is the obvious way to hand claims to a tool, and in
FastMCP's default stateful mode it is wrong in a way that does not announce
itself. Stateful sessions run every tool in the task that was started by the
*initialize* request, so a ContextVar set on a later request is invisible: the
tool keeps reading the identity of whoever opened the session. Measured, not
assumed — a session opened with one token and driven with a second executes
tools under the first. That is the confused-deputy bug this whole architecture
exists to prevent, arriving through the back door.

So: `stateless_http=True` on the server, and claims read from the per-request
ASGI scope, which is per-request by construction under either mode.

WHAT THIS MIDDLEWARE LETS PAST WITHOUT A TOKEN
----------------------------------------------
Exactly two things: the `lifespan` scope, because the streamable-HTTP session
manager starts there and an unauthenticated startup event is not a request; and
`GET /healthz`, which is liveness only.

Everything else is either validated or closed. An earlier version passed *every*
non-`http` scope through on the reasoning that lifespan needed it — which would
have handed any future scope type, websocket included, straight to the
application with no token checked. There is no websocket route on these servers
today, so it was not exploitable; it was a trapdoor left open for whoever adds
one. Closed by allowlisting `lifespan` rather than denying `http`.
"""

from __future__ import annotations

from typing import Any

from harness_auth import AuthError, Claims, audit_event, verify_token
from mcp.server.fastmcp import Context
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

# Liveness only: no auth, no downstream calls. The healthcheck must not need a
# token, or a dead identity-stub would mark every MCP server unhealthy too.
HEALTHZ_PATH = "/healthz"

# DNS-rebinding protection, kept on and told the truth about our hostnames.
#
# FastMCP switches this on by itself when the bind host is loopback, with an
# allowlist of localhost only — which passes for the test suite on
# 127.0.0.1:802x and answers 421 Misdirected Request to the orchestrator, whose
# requests carry `Host: mcp-colleague:8021`. The tempting fix is to turn the
# protection off. Don't: it is what stops a browser on a developer's machine
# from being lured into driving these servers by a hostile page. Naming the
# hosts we actually answer to keeps the control and fixes the bug.
#
# One list for all four servers, so this file stays byte-identical across the
# stamps. A server accepting a sibling's name in a Host header costs nothing —
# every name here is one of ours.
TRANSPORT_SECURITY = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "mcp-colleague:*", "mcp-canvas:*", "mcp-kuali:*", "mcp-labor:*",
        "127.0.0.1:*", "localhost:*", "[::1]:*",
    ],
    allowed_origins=[
        "http://mcp-colleague:*", "http://mcp-canvas:*", "http://mcp-kuali:*", "http://mcp-labor:*",
        "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
    ],
)

# Where the verified claims ride between the middleware and the tool.
SCOPE_KEY = "harness_claims"


class BearerAuthMiddleware:
    """Validate the Bearer token on every request, before any tool dispatch.

    Plain ASGI rather than Starlette's BaseHTTPMiddleware: this wraps the app
    FastMCP built, and lifespan events must pass straight through so the
    streamable-HTTP session manager still starts.

    No caching of decisions. Every request re-verifies — signature, issuer,
    audience, expiry — because this server trusts nothing upstream, including
    itself a moment ago.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        # Allowlist, not denylist. Only these two reach the app unauthenticated.
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self._close_unauthenticated(scope, receive, send)
            return

        if scope.get("path") == HEALTHZ_PATH:
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1")
                   for key, value in scope.get("headers") or []}
        header = headers.get("authorization", "")
        token_type, _, credential = header.partition(" ")

        if token_type.lower() != "bearer" or not credential.strip():
            await self._reject(scope, receive, send, "Authorization header missing or malformed")
            return

        try:
            claims = await verify_token(credential.strip())
        except AuthError as exc:
            await self._reject(scope, receive, send, str(exc))
            return

        scope[SCOPE_KEY] = claims
        await self.app(scope, receive, send)

    async def _close_unauthenticated(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Refuse a connection type this middleware cannot authenticate.

        The app is never called, so no route matches and no tool code runs.

        For a websocket the handshake is answered by closing rather than
        accepting: consume the `websocket.connect` and send `websocket.close`
        with 1008 (policy violation). Closing before accepting means the upgrade
        never completes — the client gets a refusal, not a socket, and nothing
        is echoed back to it.

        Any other scope type is dropped without a reply. Refusing to speak a
        protocol we have not audited is the safe default; a future scope type
        has to be added here deliberately.
        """
        if scope["type"] == "websocket":
            message = await receive()
            if message.get("type") == "websocket.connect":
                await send({"type": "websocket.close", "code": 1008})
        await audit_event(
            "auth_failed",
            detail={"reason": f"{scope['type']} connections are not served by this server"},
        )

    async def _reject(self, scope: dict[str, Any], receive: Any, send: Any, reason: str) -> None:
        """401, audited, saying nothing about the credential it just rejected."""
        await audit_event("auth_failed", detail={"reason": reason})
        response = JSONResponse(
            {"detail": "Invalid or expired token"},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="harness-poc"'},
        )
        await response(scope, receive, send)


def caller(ctx: Context) -> Claims:
    """The verified identity behind the tool call currently executing.

    Fails closed. If the claims are not on the scope then the middleware did
    not run, and the safe reading of that is "unauthenticated", never "carry on
    without a caller".
    """
    request = getattr(ctx.request_context, "request", None)
    claims = getattr(request, "scope", {}).get(SCOPE_KEY) if request is not None else None
    if not isinstance(claims, Claims):
        raise PermissionError("this request carried no verified identity")
    return claims
