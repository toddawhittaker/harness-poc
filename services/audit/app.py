"""audit — the receipts (SPEC §4.8).

Append-only event log plus a self-contained viewer page. This is what goes on
the projector for demo moments 4 and 9: every question, every refusal, who
asked, under which role.

No token validation here. SPEC §6 names the six services that must 401 without
a token — gateway, orchestrator, and the four MCP servers — and audit is not
among them: the viewer has to be readable on a screen without a login, and
services post to it fire-and-forget.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

DB_PATH = Path(os.environ.get("AUDIT_DB_PATH", "/data/audit.db"))
VIEWER_PATH = Path(__file__).parent / "viewer.html"

# Nothing matching these ever gets written, no matter what a caller sends.
# harness_auth already keeps tokens out of audit fields; this is the backstop
# for a careless caller in a later session.
#
# Whole keys, not substrings: "token" as a substring would silently swallow the
# prompt_tokens / completion_tokens counts that Session 2 will want to record,
# while claiming a redaction happened.
REDACTED_KEYS = frozenset({
    "authorization", "token", "access_token", "refresh_token", "id_token",
    "bearer", "jwt", "password", "secret", "api_key", "apikey",
})

# A careless caller is at least as likely to dump a whole header string as to
# name a field "authorization", so values get checked too.
JWT_SHAPED = re.compile(r"eyJ[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]+){0,2}")
BEARER_CREDENTIAL = re.compile(r"(?i)\bbearer\s+\S+")

REDACTION_MARKER = "[redacted]"
REDACTED_FIELDS_KEY = "redacted_fields"

app = FastAPI(title="audit")
_lock = threading.Lock()


class AuditEvent(BaseModel):
    ts: str | None = None
    service: str
    event: str
    sub: str | None = None
    roles: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


DB = connect()
DB.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        service TEXT NOT NULL,
        event TEXT NOT NULL,
        sub TEXT,
        roles TEXT NOT NULL,
        detail TEXT NOT NULL
    )
""")
DB.commit()


def _walk(node: Any, dropped: list[str], path: str) -> Any:
    """Recursively strip credentials, collecting the paths that were touched."""
    if isinstance(node, dict):
        cleaned: dict[str, Any] = {}
        for key, value in node.items():
            here = f"{path}.{key}" if path else str(key)
            if str(key).lower() in REDACTED_KEYS:
                dropped.append(here)
                continue
            cleaned[key] = _walk(value, dropped, here)
        return cleaned

    if isinstance(node, list):
        return [_walk(value, dropped, f"{path}[{n}]") for n, value in enumerate(node)]

    if isinstance(node, str):
        scrubbed = BEARER_CREDENTIAL.sub(REDACTION_MARKER, JWT_SHAPED.sub(REDACTION_MARKER, node))
        if scrubbed != node:
            dropped.append(path or "(value)")
        return scrubbed

    return node


def scrub(detail: dict[str, Any]) -> dict[str, Any]:
    """Strip credentials at any depth, and record where something was stripped.

    Storing a sensitive key with a "[redacted]" value would still leave an
    `authorization` field in the log for the next careless reader to grep past.
    Dropping the key and naming it in `redacted_fields` keeps the signal without
    keeping the secret. The names are safe to record: audit keys are static
    strings written by our own code, never caller data.
    """
    # Reserved, so a caller cannot pre-seed it and make the record lie.
    detail = {k: v for k, v in detail.items() if k != REDACTED_FIELDS_KEY}

    dropped: list[str] = []
    cleaned = _walk(detail, dropped, "")
    if dropped:
        cleaned[REDACTED_FIELDS_KEY] = sorted(set(dropped))
    return cleaned


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events", status_code=204)
def post_event(event: AuditEvent) -> Response:
    ts = event.ts or datetime.now(UTC).isoformat(timespec="seconds")
    with _lock:
        DB.execute(
            "INSERT INTO events (ts, service, event, sub, roles, detail) VALUES (?,?,?,?,?,?)",
            (ts, event.service, event.event, event.sub,
             json.dumps(event.roles), json.dumps(scrub(event.detail))),
        )
        DB.commit()
    return Response(status_code=204)


@app.get("/events")
def get_events(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 1000))
    with _lock:
        rows = DB.execute(
            "SELECT id, ts, service, event, sub, roles, detail"
            " FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": row["id"],
            "ts": row["ts"],
            "service": row["service"],
            "event": row["event"],
            "sub": row["sub"],
            "roles": json.loads(row["roles"]),
            "detail": json.loads(row["detail"]),
        }
        for row in rows
    ]


@app.get("/")
def viewer() -> FileResponse:
    return FileResponse(VIEWER_PATH, media_type="text/html")
