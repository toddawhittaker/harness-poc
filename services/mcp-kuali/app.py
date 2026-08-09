"""mcp-kuali — fake curriculum (SPEC §4.7).

Low-sensitivity data, identical mechanism: every request re-validates the Bearer
token, every call is audited.

The skill tags on course outcomes come from the same controlled vocabulary as
mcp-labor's occupation skills (SPEC §5). The strings match exactly, on purpose:
that is what turns "which occupations would this graduate qualify for" into a
real join between curriculum and the labor market, instead of the model
deciding two differently-worded phrases sound similar.
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
from rules import (
    CURRICULUM_ROLES,
    UnknownProgram,
    audited,
    require_any_role,
    require_role,
)

DB_PATH = Path(os.environ.get("KUALI_DB_PATH", "/data/kuali.db"))

# Stateless: see the long note in mcp_auth.py about why a stateful session
# would let a tool read the identity of whoever opened it.
mcp = FastMCP("kuali", stateless_http=True, transport_security=TRANSPORT_SECURITY)

_lock = threading.Lock()
_db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
_db.row_factory = sqlite3.Row


def query(sql: str, *params: object) -> list[sqlite3.Row]:
    with _lock:
        return _db.execute(sql, params).fetchall()


class CurriculumCourse(BaseModel):
    course_code: str
    title: str
    credits: int
    sequence: int
    prereqs: list[str]


class ProgramCurriculum(BaseModel):
    program_code: str
    program_name: str
    courses: list[CurriculumCourse]


class CourseOutcome(BaseModel):
    course_code: str
    outcome_id: str
    text: str
    skill: str


class ProgramOutcomes(BaseModel):
    program_code: str
    program_name: str
    outcomes: list[CourseOutcome]
    skills_covered: list[str]


class CatalogProgram(BaseModel):
    program_code: str
    name: str
    cip_code: str


def program_name(program_code: str) -> str:
    rows = query("SELECT name FROM programs WHERE code = ?", program_code)
    if not rows:
        raise UnknownProgram(f"unknown program code {program_code}")
    return rows[0]["name"]


def split_prereqs(raw: str | None) -> list[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: object) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.tool()
async def get_program_curriculum(program_code: str, ctx: Context) -> ProgramCurriculum:
    """The required course sequence for one program, with credits and prerequisites."""
    claims = caller(ctx)
    async with audited("get_program_curriculum", claims, {"program_code": program_code}):
        require_any_role(claims, CURRICULUM_ROLES, "get_program_curriculum")
        name = program_name(program_code)
        rows = query("SELECT * FROM curriculum WHERE program_code = ?"
                     " ORDER BY sequence, course_code", program_code)
        return ProgramCurriculum(
            program_code=program_code,
            program_name=name,
            courses=[CurriculumCourse(
                course_code=row["course_code"], title=row["title"], credits=row["credits"],
                sequence=row["sequence"], prereqs=split_prereqs(row["prereqs"]),
            ) for row in rows],
        )


@mcp.tool()
async def get_course_outcomes(program_code: str, ctx: Context) -> ProgramOutcomes:
    """Learning outcomes for every course in a program, each tagged with a skill drawn from the SAME controlled vocabulary as mcp-labor's occupation skills, so the two sets can be matched by exact string. This is the evidence for whether a program's graduates would qualify for an occupation."""
    claims = caller(ctx)
    async with audited("get_course_outcomes", claims, {"program_code": program_code}):
        require_any_role(claims, CURRICULUM_ROLES, "get_course_outcomes")
        name = program_name(program_code)
        rows = query("SELECT * FROM outcomes WHERE program_code = ?"
                     " ORDER BY course_code, outcome_id", program_code)
        outcomes = [CourseOutcome(
            course_code=row["course_code"], outcome_id=row["outcome_id"],
            text=row["text"], skill=row["skill"],
        ) for row in rows]
        return ProgramOutcomes(
            program_code=program_code, program_name=name, outcomes=outcomes,
            # Deduplicated up front so the caller matching these against
            # occupation skills does not have to.
            skills_covered=sorted({outcome.skill for outcome in outcomes}),
        )


@mcp.tool()
async def list_programs_catalog(ctx: Context) -> list[CatalogProgram]:
    """Every program in the catalog with its code and CIP code. The left side of a curriculum gap analysis."""
    claims = caller(ctx)
    async with audited("list_programs_catalog", claims, {}):
        require_role(claims, "dean", "list_programs_catalog")
        return [CatalogProgram(program_code=row["code"], name=row["name"], cip_code=row["cip_code"])
                for row in query("SELECT * FROM programs ORDER BY code")]


app = BearerAuthMiddleware(mcp.streamable_http_app())
