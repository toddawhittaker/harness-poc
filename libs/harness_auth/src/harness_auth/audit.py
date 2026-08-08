"""Fire-and-forget audit client (SPEC §2).

Every service reports what it did to the audit service. Auditing must never
change the outcome of a request: if the audit service is down, slow, or
returning errors, the caller carries on and the event is lost. An audit trail
that can take the harness down is a liability, not a control.

Never pass a raw token, an Authorization header, or a password in `detail`.
The audit service drops such keys defensively, but the rule is upstream: tokens
do not leave the process that validated them.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

AUDIT_URL = os.environ.get("HARNESS_AUDIT_URL", "http://audit:8030/events")
SERVICE_NAME = os.environ.get("HARNESS_SERVICE_NAME", "unknown")
TIMEOUT_SECONDS = 2.0

# create_task keeps only a weak reference, so a task with no other referent can
# be garbage collected mid-flight. Holding them here until they finish is the
# documented way to avoid that.
_in_flight: set[asyncio.Task[None]] = set()


async def _post(payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            await client.post(AUDIT_URL, json=payload)
    except Exception:  # noqa: BLE001 — auditing must never break the caller
        pass


async def audit_event(
    event: str,
    *,
    service: str | None = None,
    sub: str | None = None,
    roles: list[str] | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Queue one event and return immediately.

    Scheduled rather than awaited: the caller must not wait on the audit
    service. `bearer_claims` audits before raising its 401, so awaiting the POST
    would let anyone flooding bad tokens pin a request worker for the timeout
    on every attempt, using the audit trail as the lever.
    """
    payload = {
        "service": service or SERVICE_NAME,
        "event": event,
        "sub": sub,
        "roles": roles or [],
        "detail": detail or {},
    }
    try:
        task = asyncio.create_task(_post(payload))
    except RuntimeError:
        # No running loop (a sync caller, or interpreter shutdown). Losing the
        # event is the correct trade — auditing never breaks the caller.
        return
    _in_flight.add(task)
    task.add_done_callback(_in_flight.discard)
