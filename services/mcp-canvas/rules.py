"""Authorization rules and the audit of every tool call (SPEC §4.6).

DUPLICATED, DELIBERATELY — see the header of mcp_auth.py for the reasoning and
for the safety condition that makes it acceptable.

The rule that matters here is the faculty/dean asymmetry, and it is a record
rule rather than a role rule: faculty hold a real entitlement to section
engagement data, scoped to the sections they actually teach. Faculty see their
rooms; the dean sees the building. Same tool, same server, same second — the
answer depends only on the role in the caller's own token.

EVERY CALL IS AUDITED, ALLOWED OR REFUSED. Calls arriving through the
orchestrator produce a second row there. That is intentional, not redundant:
two independent records from two independent enforcement layers, and the bypass
demo depends on this row existing when the gateway never saw the request. Do not
"deduplicate" them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any

from harness_auth import Claims, audit_event
from mcp.server.fastmcp.exceptions import ToolError


def refuse(message: str) -> ToolError:
    """A refusal the orchestrator's model can relay unchanged."""
    return ToolError(message)


def require_role(claims: Claims, role: str, tool: str) -> None:
    """Gate a tool on a single role."""
    if role not in claims.roles:
        raise refuse(f"{tool} requires the {role} role.")


def require_section_access(claims: Claims, section_id: str, own_sections: Iterable[str]) -> None:
    """The record-level check: this instructor, this section.

    A dean reads any section. A faculty member reads the sections they teach,
    and the refusal for anything else is fixed word for word by SPEC §4.6 —
    it names the section and it names who the cross-section view belongs to,
    so the boundary is legible rather than merely felt. Tests assert it verbatim.
    """
    if "dean" in claims.roles:
        return
    if "faculty" not in claims.roles:
        raise refuse("get_section_engagement requires the faculty or dean role.")
    if section_id not in set(own_sections):
        raise refuse(
            f"Section {section_id} is not among your assigned sections; "
            "cross-section views belong to the dean."
        )


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
