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
    """
    detail: dict[str, Any] = {"tool": tool, "args_hash": _args_hash(args)}
    try:
        yield
    except ToolError as exc:
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={**detail, "decision": "refused", "reason": str(exc)},
        )
        raise
    except Exception as exc:  # noqa: BLE001
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={**detail, "decision": "refused", "reason": type(exc).__name__},
        )
        raise
    await audit_event(
        "tool_call", sub=claims.sub, roles=claims.roles,
        detail={**detail, "decision": "ok"},
    )
