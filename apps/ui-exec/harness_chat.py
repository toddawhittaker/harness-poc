"""The whole of a harness surface (SPEC §4.9).

This file is byte-identical in apps/ui-advisor and apps/ui-exec, the way
mcp_auth.py is byte-identical across the four MCP servers, and for the same
reason: two copies that must stay the same are easier to read on a projector
than one shared package with an import path to explain, and
tests/test_ui_apps.py fails if they ever drift.

What a surface does, in full:

  1. Exchange a persona and password with identity-stub for a real RS256 JWT.
     The UI mints nothing and validates nothing — it asks the issuer, and takes
     yes or no for an answer.
  2. Hold that token server-side for the session, and hold the conversation
     client-side, so the harness itself stays stateless (SPEC §4.9).
  3. POST every message to the gateway with the token in an Authorization
     header, and render what comes back.

What a surface deliberately does NOT do: decide anything. No role checks, no
tool lists, no model calls, no API keys. Access follows the token's roles, not
the app, which is why any persona can log into either app and why logging pat
into the executive app during Q&A proves the point rather than breaking it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import chainlit as cl
import httpx

IDENTITY_URL = os.environ.get("IDENTITY_URL", "http://identity-stub:8001")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8000")

# A question that reaches a model and four tool servers is not a 10-second
# question. Long enough that a real answer arrives, short enough that a wedged
# stack says so while the room is still watching.
REQUEST_TIMEOUT = 120.0


@dataclass(frozen=True)
class Branding:
    """Everything that differs between the two apps."""

    name: str
    greeting: str
    starters: list[tuple[str, str]]


# persona id -> that persona's harness JWT, for the life of this process.
#
# NOT in cl.User.metadata, which is the obvious place and the wrong one:
# Chainlit serves the user object to the browser from GET /user, so a token
# parked there would be readable by any script on the page. The Chainlit session
# cookie carries only the persona id; the bearer token never leaves this
# process except in the Authorization header of a call to the gateway.
_TOKENS: dict[str, str] = {}


async def authenticate(username: str, password: str) -> cl.User | None:
    """Trade a persona and password for a real token, or refuse.

    No local password list, no fallback, no dev-mode shortcut: identity-stub is
    the only thing here that knows whether a credential is good, and a
    non-200 is a no. An unreachable issuer is also a no — failing open at a
    login screen would be the one place in this system where a layer trusted
    itself.
    """
    persona = username.strip().lower()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{IDENTITY_URL}/token",
                json={"persona": persona, "password": password},
            )
            if response.status_code != 200:
                return None
            _TOKENS[persona] = response.json()["access_token"]
            # The display name comes from the issuer's public directory, not
            # from a list in here and not by decoding the token: an unverified
            # read of a JWT is exactly the habit this codebase does not want.
            directory = await client.get(f"{IDENTITY_URL}/personas")
    except httpx.HTTPError:
        return None

    names = {entry["id"]: entry["name"] for entry in directory.json()} \
        if directory.status_code == 200 else {}
    return cl.User(identifier=persona, display_name=names.get(persona, persona))


def _token() -> str | None:
    user = cl.user_session.get("user")
    return _TOKENS.get(user.identifier) if user else None


async def start_chat(brand: Branding) -> None:
    """Open a session: empty history, and a greeting that names who is signed in."""
    cl.user_session.set("history", [])
    user = cl.user_session.get("user")
    who = getattr(user, "display_name", None) or getattr(user, "identifier", "there")
    await cl.Message(content=brand.greeting.format(who=who)).send()


def _suffix(tools_used: list[str]) -> str:
    """The receipts line under an answer.

    Inline code rather than a heading or a bold line: it should be legible from
    the back of a room without competing with the answer for attention. An empty
    list is stated rather than hidden — "no tools" is the whole story in demo
    moment 3, where a refusal never leaves the gateway.
    """
    if not tools_used:
        return "\n\n`no tools called`"
    return "\n\n`tools: " + ", ".join(tools_used) + "`"


async def answer(message: cl.Message) -> None:
    """One turn: post to the gateway with the caller's own token, render the reply."""
    token = _token()
    if token is None:
        await cl.Message(
            content="Your session has expired. Please reload the page and sign in again."
        ).send()
        return

    history: list[dict[str, str]] = cl.user_session.get("history") or []
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{GATEWAY_URL}/chat",
                json={"message": message.content, "history": history},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        await cl.Message(
            content="The harness did not respond. It may be starting up — please try again."
        ).send()
        return

    if response.status_code == 401:
        _TOKENS.pop(cl.user_session.get("user").identifier, None)
        await cl.Message(
            content="Your sign-in is no longer valid. Please reload the page and sign in again."
        ).send()
        return
    if response.status_code != 200:
        # The body can carry detail that is not for a projector; the status is
        # enough for the room and the audit page has the rest.
        await cl.Message(
            content="The harness could not complete that request. Please try again."
        ).send()
        return

    payload = response.json()
    reply = payload.get("reply", "")
    await cl.Message(content=reply + _suffix(payload.get("tools_used") or [])).send()

    # The harness is stateless; this session holds the conversation and hands it
    # back on the next turn (SPEC §4.9).
    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": reply})
    cl.user_session.set("history", history)


def starters(brand: Branding) -> list[cl.Starter]:
    return [cl.Starter(label=label, message=text) for label, text in brand.starters]
