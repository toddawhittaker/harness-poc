"""mcp-canvas — fake LMS, the current-data source (SPEC §4.6).

Canvas is the pulse: who logged in this week, what was submitted, what is
missing. Colleague is the record and knows what comes next term. Keying both to
the same student ids is what lets one question join them.

Same skeleton as mcp-colleague: every request re-validates the Bearer token,
every tool re-checks roles and record assignments, every call is audited.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel
from starlette.responses import JSONResponse

from mcp_auth import TRANSPORT_SECURITY, BearerAuthMiddleware, caller
from rules import audited, require_role, require_section_access

DB_PATH = Path(os.environ.get("CANVAS_DB_PATH", "/data/canvas.db"))

# Stateless: see the long note in mcp_auth.py about why a stateful session
# would let a tool read the identity of whoever opened it.
mcp = FastMCP("canvas", stateless_http=True, transport_security=TRANSPORT_SECURITY)

_lock = threading.Lock()
_db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
_db.row_factory = sqlite3.Row


def query(sql: str, *params: object) -> list[sqlite3.Row]:
    with _lock:
        return _db.execute(sql, params).fetchall()


class SectionSummary(BaseModel):
    section_id: str
    course_code: str
    program_code: str
    term: str
    enrollment: int
    pct_logged_in_this_week: float
    missing_submissions: int


class StudentActivity(BaseModel):
    student_id: str
    name: str
    last_login_days: int
    submitted: int
    missing: int


class SectionEngagement(BaseModel):
    section_id: str
    course_code: str
    instructor_name: str
    enrollment: int
    pct_logged_in_this_week: float
    missing_submissions: int
    students: list[StudentActivity]


class ProgramEngagement(BaseModel):
    program_code: str
    sections: int
    enrollment: int
    pct_logged_in_this_week: float
    missing_submissions: int


# "This week" means a login within the last seven days. One definition, used by
# every tool here, so the section view and the rollup cannot disagree.
ACTIVE_WITHIN_DAYS = 7


def own_section_ids(instructor_sub: str) -> list[str]:
    return [row["section_id"] for row in
            query("SELECT section_id FROM faculty_assignments WHERE instructor_sub = ?"
                  " ORDER BY section_id", instructor_sub)]


def activity_stats(rows: list[sqlite3.Row]) -> tuple[int, float, int]:
    """Enrollment, share active this week, and total missing submissions."""
    enrollment = len(rows)
    if not enrollment:
        return 0, 0.0, 0
    active = sum(1 for row in rows if row["last_login_days"] <= ACTIVE_WITHIN_DAYS)
    missing = sum(row["missing"] for row in rows)
    return enrollment, round(100.0 * active / enrollment, 1), missing


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: object) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.tool()
async def get_my_sections(ctx: Context) -> list[SectionSummary]:
    """The sections you teach this term, with enrollment, share of students active this week, and missing submissions."""
    claims = caller(ctx)
    async with audited("get_my_sections", claims, {}):
        require_role(claims, "faculty", "get_my_sections")
        summaries: list[SectionSummary] = []
        for section_id in own_section_ids(claims.sub):
            rows = query("SELECT * FROM sections WHERE id = ?", section_id)
            if not rows:
                continue
            section = rows[0]
            enrollment, pct_active, missing = activity_stats(
                query("SELECT * FROM activity WHERE section_id = ?", section_id))
            summaries.append(SectionSummary(
                section_id=section["id"], course_code=section["course_code"],
                program_code=section["program_code"], term=section["term"],
                enrollment=enrollment, pct_logged_in_this_week=pct_active,
                missing_submissions=missing,
            ))
        return summaries


@mcp.tool()
async def get_section_engagement(section_id: str, ctx: Context) -> SectionEngagement:
    """Per-student engagement for one section: days since last login, submissions in, submissions missing."""
    claims = caller(ctx)
    async with audited("get_section_engagement", claims, {"section_id": section_id}):
        # The boundary check runs before the section is read, so a refusal
        # cannot be told apart from a refusal about a section that does not
        # exist — probing for real section ids gets you nothing.
        require_section_access(claims, section_id, own_section_ids(claims.sub))
        rows = query("SELECT * FROM sections WHERE id = ?", section_id)
        if not rows:
            raise ValueError(f"no section {section_id}")
        section = rows[0]

        activity = query("SELECT * FROM activity WHERE section_id = ?", section_id)
        names = {row["student_id"]: row["student_name"] for row in
                 query("SELECT student_id, student_name FROM section_enrollment WHERE section_id = ?",
                       section_id)}
        enrollment, pct_active, missing = activity_stats(activity)
        return SectionEngagement(
            section_id=section["id"], course_code=section["course_code"],
            instructor_name=section["instructor_name"], enrollment=enrollment,
            pct_logged_in_this_week=pct_active, missing_submissions=missing,
            students=sorted(
                (StudentActivity(
                    student_id=row["student_id"], name=names.get(row["student_id"], row["student_id"]),
                    last_login_days=row["last_login_days"], submitted=row["submitted"],
                    missing=row["missing"],
                ) for row in activity),
                key=lambda student: student.student_id,
            ),
        )


@mcp.tool()
async def get_program_engagement_rollup(ctx: Context, program_code: str | None = None) -> list[ProgramEngagement]:
    """Current-week engagement aggregated per program, or for one program if program_code is given."""
    claims = caller(ctx)
    async with audited("get_program_engagement_rollup", claims, {"program_code": program_code}):
        require_role(claims, "dean", "get_program_engagement_rollup")
        if program_code:
            sections = query("SELECT * FROM sections WHERE program_code = ? ORDER BY id", program_code)
        else:
            sections = query("SELECT * FROM sections ORDER BY program_code, id")

        by_program: dict[str, list[sqlite3.Row]] = {}
        counts: dict[str, int] = {}
        for section in sections:
            counts[section["program_code"]] = counts.get(section["program_code"], 0) + 1
            by_program.setdefault(section["program_code"], []).extend(
                query("SELECT * FROM activity WHERE section_id = ?", section["id"]))

        rollup: list[ProgramEngagement] = []
        for code, rows in sorted(by_program.items()):
            enrollment, pct_active, missing = activity_stats(rows)
            rollup.append(ProgramEngagement(
                program_code=code, sections=counts[code], enrollment=enrollment,
                pct_logged_in_this_week=pct_active, missing_submissions=missing,
            ))
        return rollup


app = BearerAuthMiddleware(mcp.streamable_http_app())
