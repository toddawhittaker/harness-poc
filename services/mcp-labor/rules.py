"""Authorization rules and the audit of every tool call (SPEC §4.5).

DUPLICATED, DELIBERATELY — see the header of mcp_auth.py for the reasoning and
for the safety condition that makes it acceptable.

Labor-market data is public, and this server still validates every token and
audits every call. That is the point worth saying out loud in the demo: the
mechanism does not soften because the data is harmless. A server that enforces
only when the data is sensitive is a server whose enforcement was never
structural.

EVERY CALL IS AUDITED, ALLOWED OR REFUSED. Calls arriving through the
orchestrator produce a second row there. That is intentional, not redundant:
two independent records from two independent enforcement layers, and the bypass
demo depends on this row existing when the gateway never saw the request. Do not
"deduplicate" them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from harness_auth import Claims, audit_event
from mcp.server.fastmcp.exceptions import ToolError

# What the caller is told when this server faults. Deliberately says nothing:
# the model must not be handed a stack detail to improvise around.
INTERNAL_ERROR = "Internal error handling this request."


class UnknownOccupation(ValueError):
    """A SOC code this server does not track.

    A bad argument, not an authorization decision. It exists so `audited` can
    tell the two apart by TYPE rather than by reading a message — a refusal in
    the audit trail must always mean somebody was told no. Nothing on this
    server refuses anybody, so without it every mistyped code would be the only
    amber row this server ever wrote.
    """


def refuse(message: str) -> ToolError:
    """A refusal the orchestrator's model can relay unchanged."""
    return ToolError(message)


def _args_hash(args: dict[str, Any]) -> str:
    """A short, stable digest of the arguments — a correlation key, not a privacy
    measure. It collapses arbitrary tool arguments to twelve stable characters so
    two rows can be recognised as the same question."""
    payload = json.dumps(args, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


@asynccontextmanager
async def audited(tool: str, claims: Claims, args: dict[str, Any]) -> AsyncIterator[None]:
    """Wrap a tool body so exactly one audit row is written, whatever happens.

    Fire-and-forget: `audit_event` schedules the POST and returns. A tool must
    never wait on the audit service.

    Three outcomes, told apart by exception TYPE and never by message text:
    a refusal this module raised on purpose, a caller who named something that
    does not exist, and a fault in this server. Only the first is `refused` —
    an amber row in the audit viewer must always mean somebody was told no.
    Public data does not soften the mechanism, and it does not soften this
    either: the tiers are the same three on all four servers.
    """
    detail: dict[str, Any] = {"tool": tool, "args_hash": _args_hash(args)}
    try:
        yield
    except ToolError as exc:
        # A deliberate refusal. Its message is written to be read by the person
        # who asked, so it is safe to record and safe to relay.
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={**detail, "decision": "refused", "reason": str(exc)},
        )
        raise
    except UnknownOccupation as exc:
        # Bad input, not a boundary. The message is our own and names only the
        # code the caller supplied, so it goes to both the trail and the model.
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={**detail, "decision": "error", "reason": str(exc)},
        )
        raise
    except Exception as exc:  # noqa: BLE001
        # A fault in this server. The class name only — str(exc) can carry file
        # paths or SQL fragments — and the caller gets a fixed sentence rather
        # than our internals.
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={**detail, "decision": "error", "reason": type(exc).__name__},
        )
        # ToolError directly, not refuse(): this is a fault, and nothing in this
        # file may dress a fault up as somebody being told no.
        raise ToolError(INTERNAL_ERROR) from exc
    await audit_event(
        "tool_call", sub=claims.sub, roles=claims.roles,
        detail={**detail, "decision": "ok"},
    )
