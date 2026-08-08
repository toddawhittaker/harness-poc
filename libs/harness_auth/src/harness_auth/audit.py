"""Fire-and-forget audit client (SPEC §2).

Every service reports what it did to the audit service. Auditing must never
change the outcome of a request: if the audit service is down, slow, or
returning errors, the caller carries on and the event is lost. An audit trail
that can take the harness down is a liability, not a control.

Lost, but never silently. A dropped event leaves one WARNING line naming the
event and the URL that would not take it — enough to tell a misconfigured
HARNESS_AUDIT_URL from a stopped container in the ten seconds before a demo,
instead of discovering an empty audit page in front of the room.

Never pass a raw token, an Authorization header, or a password in `detail`.
The audit service drops such keys defensively, but the rule is upstream: tokens
do not leave the process that validated them.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

AUDIT_URL = os.environ.get("HARNESS_AUDIT_URL", "http://audit:8030/events")
SERVICE_NAME = os.environ.get("HARNESS_SERVICE_NAME", "unknown")
TIMEOUT_SECONDS = 2.0

logger = logging.getLogger("harness_auth.audit")

# create_task keeps only a weak reference, so a task with no other referent can
# be garbage collected mid-flight. Holding them here until they finish is the
# documented way to avoid that.
_in_flight: set[asyncio.Task[None]] = set()


def _dropped(event: str, url: str, cause: str) -> None:
    """One line, naming the event and the URL. Never the detail payload.

    `detail` holds whatever a caller put there, and a dropped-event log is the
    one place that must not become the leak the audit service is careful to
    prevent. The event name and the target URL are enough to diagnose this,
    and neither is caller data.
    """
    logger.warning("audit event %r dropped: POST %s failed (%s)", event, url, cause)


async def _post(payload: dict[str, Any]) -> None:
    event = payload.get("event", "?")
    # Capture the URL rather than re-reading the global when logging: the line
    # has to name the request that actually failed, or it misleads exactly when
    # someone is reading it under pressure.
    url = AUDIT_URL
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
        # A non-2xx is a dropped event too. Without this check a misconfigured
        # HARNESS_AUDIT_URL pointing at some other service's 404 looks exactly
        # like success, and the audit page is simply, inexplicably empty.
        if response.status_code >= 400:
            _dropped(event, url, f"HTTP {response.status_code}")
    except Exception as exc:  # noqa: BLE001 — auditing must never break the caller
        _dropped(event, url, f"{type(exc).__name__}: {exc}")


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
    except RuntimeError as exc:
        # No running loop (a sync caller, or interpreter shutdown). Losing the
        # event is the correct trade — auditing never breaks the caller — but
        # it still gets a breadcrumb.
        _dropped(event, AUDIT_URL, f"RuntimeError: {exc}")
        return
    _in_flight.add(task)
    task.add_done_callback(_in_flight.discard)
