"""Authorization rules and the audit of every tool call (SPEC §4.4).

DUPLICATED, DELIBERATELY — see the header of mcp_auth.py for the reasoning and
for the safety condition that makes it acceptable.

Two things live here so no tool can forget either one.

REFUSALS ARE TOOL ERRORS CARRYING TEXT A HUMAN CAN READ. Never an empty list.
An empty result reads to the model, and then to the user, as "you have no
advisees" — a wrong answer dressed as an answer. A refusal says who may ask and
why this caller may not, the model relays it, and the room sees the boundary.
Several of these sentences are fixed word for word by the spec because they are
the demo; tests assert them verbatim.

EVERY CALL IS AUDITED, ALLOWED OR REFUSED. Note this produces a second row for
calls that arrived through the orchestrator, which audits its own. That is
intentional, not redundant: two independent records from two independent
enforcement layers. The bypass demo (SPEC §7 step 4) depends on the row written
here existing when the gateway never saw the request at all. Do not
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

# What the caller is told when this server faults. Deliberately says nothing:
# the model must not be handed a stack detail to improvise around.
INTERNAL_ERROR = "Internal error handling this request."


class UnknownStudent(ValueError):
    """A student id the register does not have.

    A bad argument, not an authorization decision. It exists so `audited` can
    tell the two apart by TYPE rather than by reading a message — a refusal in
    the audit trail must always mean somebody was told no.

    Unreachable from outside on purpose: `require_assignment` runs first, so an
    id that belongs to nobody is refused as "not among your assigned advisees"
    rather than confirmed absent, and the tools never double as a way to probe
    which ids exist. What is left for this class is the genuine fault — an
    assignment row pointing at a student who is not in the register.
    """


# SPEC §4.4, fixed word for word. This line is the RBAC demo.
DEAN_INDIVIDUAL_RECORD = (
    "Individual student records require an advisor assignment; deans receive aggregates."
)


def refuse(message: str) -> ToolError:
    """A refusal the orchestrator's model can relay unchanged."""
    return ToolError(message)


def require_role(claims: Claims, role: str, tool: str) -> None:
    """Gate a tool on a single role."""
    if role not in claims.roles:
        raise refuse(f"{tool} requires the {role} role.")


def require_advisor_for_record(claims: Claims, tool: str) -> None:
    """Gate an individual student record.

    A dean gets the spec's exact sentence rather than the generic one: they hold
    real privilege here, just not this kind, and saying so is the whole point of
    the moment. Someone holding both roles is treated as an advisor, because
    they have the assignment the rule is actually about.
    """
    if "advisor" in claims.roles:
        return
    if "dean" in claims.roles:
        raise refuse(DEAN_INDIVIDUAL_RECORD)
    raise refuse(f"{tool} requires the advisor role.")


def require_assignment(claims: Claims, student_id: str, advisees: Iterable[str]) -> None:
    """The record-level check: this advisor, this student.

    Holding the advisor role is not enough. Every advisee of every other
    advisor is out of reach, and the refusal names the student so the boundary
    is legible rather than merely felt.
    """
    if student_id not in set(advisees):
        raise refuse(f"Student {student_id} is not among your assigned advisees.")


def _args_hash(args: dict[str, Any]) -> str:
    """A short, stable digest of the arguments.

    A correlation key, not a privacy measure — be clear about which, because the
    refusal text recorded a few lines below deliberately DOES name the student
    ("Student S-1042 is not among your assigned advisees."), and an audit trail
    that records which record was asked about is the point of the FERPA story,
    not a leak. Recording that boundary is what makes demo moment 9 work.

    What the hash buys is that arbitrary tool arguments — any shape, any size,
    from any future tool — collapse to twelve stable characters that still let
    two rows be recognised as the same question. Nothing here depends on it
    being one-way.
    """
    payload = json.dumps(args, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


@asynccontextmanager
async def audited(tool: str, claims: Claims, args: dict[str, Any]) -> AsyncIterator[None]:
    """Wrap a tool body so exactly one audit row is written, whatever happens.

    Fire-and-forget, like every audit call in this repo: `audit_event` schedules
    the POST and returns. A tool must never wait on the audit service, and a
    dead audit service must never turn a refusal into a 500.

    Three outcomes, told apart by exception TYPE and never by message text:
    a refusal this module raised on purpose, a caller who named something that
    does not exist, and a fault in this server. Only the first is `refused` —
    an amber row in the audit viewer must always mean somebody was told no.
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
    except UnknownStudent as exc:
        # Bad input, not a boundary. The message is our own and names only the
        # id the caller supplied, so it goes to both the trail and the model.
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={**detail, "decision": "error", "reason": str(exc)},
        )
        raise
    except Exception as exc:  # noqa: BLE001
        # A fault in this server. The class name only — str(exc) could carry a
        # row of student data — and the caller gets a fixed sentence rather than
        # our internals. A tool that fails silently is worse than one that fails
        # loudly, so the row is still written.
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
