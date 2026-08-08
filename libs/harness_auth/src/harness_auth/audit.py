"""Fire-and-forget audit client (SPEC §2).

Every service reports what it did to the audit service. Auditing must never
change the outcome of a request: if the audit service is down, slow, or
returning errors, the caller carries on and the event is lost. An audit trail
that can take the harness down is a liability, not a control.

Lost, but never silently. A dropped event leaves one WARNING line naming the
event, the endpoint that would not take it, and the exception class — enough
to tell a misconfigured HARNESS_AUDIT_URL from a stopped container in the ten
seconds before a demo, instead of discovering an empty audit page in front of
the room. The line is debounced to once a minute per process, so a dead audit
service warns steadily rather than drowning the log it is trying to inform.

Never pass a raw token, an Authorization header, or a password in `detail`.
The audit service drops such keys defensively, but the rule is upstream: tokens
do not leave the process that validated them.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

AUDIT_URL = os.environ.get("HARNESS_AUDIT_URL", "http://audit:8030/events")
SERVICE_NAME = os.environ.get("HARNESS_SERVICE_NAME", "unknown")
TIMEOUT_SECONDS = 2.0
LOG_DEBOUNCE_SECONDS = 60.0

# Module level, so the debounce is per process rather than per call site.
_last_warned = 0.0

logger = logging.getLogger("harness_auth.audit")

# create_task keeps only a weak reference, so a task with no other referent can
# be garbage collected mid-flight. Holding them here until they finish is the
# documented way to avoid that.
_in_flight: set[asyncio.Task[None]] = set()


def _dropped(event: str, url: str, exception_class: str) -> None:
    """One line: the event type, the endpoint, and the exception class.

    Three things are deliberately absent.

    The detail payload: it holds whatever a caller put there, and a
    dropped-event log is the one place that must not become the leak the audit
    service works to prevent.

    The exception's message: httpx embeds the full request URL, query string
    included, in several of its messages — HTTPStatusError most of all. The
    class name says what broke; the message would say it with whatever the
    query string carried.

    The query string: stripped here rather than at the call site, so no future
    caller can route around it.
    """
    global _last_warned

    # Debounced per process. A dead audit service should warn steadily enough
    # to notice during setup, not scream once per request and bury everything
    # else in the log you are trying to read.
    now = time.monotonic()
    if now - _last_warned < LOG_DEBOUNCE_SECONDS:
        return
    _last_warned = now

    logger.warning(
        "audit event %r dropped: POST %s failed (%s)",
        event, url.split("?", 1)[0], exception_class,
    )


async def _post(payload: dict[str, Any]) -> None:
    event = payload.get("event", "?")
    # Capture the URL rather than re-reading the global when logging: the line
    # has to name the request that actually failed, or it misleads exactly when
    # someone is reading it under pressure.
    url = AUDIT_URL
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            # A non-2xx is a dropped event too. Without this a misconfigured
            # HARNESS_AUDIT_URL pointing at some other service's 404 looks
            # exactly like success, and the audit page is simply, inexplicably
            # empty. No retry: fire-and-forget stays fire-and-forget.
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — auditing must never break the caller
        _dropped(event, url, type(exc).__name__)


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
        _dropped(event, AUDIT_URL, type(exc).__name__)
        return
    _in_flight.add(task)
    task.add_done_callback(_in_flight.discard)
