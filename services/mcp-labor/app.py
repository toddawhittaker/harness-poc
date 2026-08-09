"""mcp-labor — fake BLS/O*NET (SPEC §4.5).

Public data, identical mechanism: every request re-validates the Bearer token,
every call is audited. Say this in the demo — enforcement here is structural,
not a response to how sensitive the rows happen to be.

The skills strings are drawn from the same controlled vocabulary as mcp-kuali's
course outcomes (SPEC §5). That exact-string overlap is what makes the
qualification and gap syntheses real joins rather than the model free-associating.
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
from rules import UnknownOccupation, audited

DB_PATH = Path(os.environ.get("LABOR_DB_PATH", "/data/labor.db"))

# Stateless: see the long note in mcp_auth.py about why a stateful session
# would let a tool read the identity of whoever opened it.
mcp = FastMCP("labor", stateless_http=True, transport_security=TRANSPORT_SECURITY)

_lock = threading.Lock()
_db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
_db.row_factory = sqlite3.Row


def query(sql: str, *params: object) -> list[sqlite3.Row]:
    with _lock:
        return _db.execute(sql, params).fetchall()


class Occupation(BaseModel):
    soc_code: str
    title: str
    growth_pct: float
    median_wage: int
    skills: list[str]


class ProgramOccupation(BaseModel):
    program_code: str
    soc_codes: list[str]


def skills_for(soc_code: str) -> list[str]:
    return [row["skill"] for row in
            query("SELECT skill FROM occupation_skills WHERE soc_code = ? ORDER BY skill", soc_code)]


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: object) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.tool()
async def list_occupations(ctx: Context, sort_by_growth: bool = True) -> list[Occupation]:
    """All tracked occupations with projected growth, median wage, and skills. Sorted by growth by default."""
    claims = caller(ctx)
    async with audited("list_occupations", claims, {"sort_by_growth": sort_by_growth}):
        order = "growth_pct DESC" if sort_by_growth else "title ASC"
        rows = query(f"SELECT * FROM occupations ORDER BY {order}")  # noqa: S608 — not caller data
        return [Occupation(
            soc_code=row["soc_code"], title=row["title"], growth_pct=row["growth_pct"],
            median_wage=row["median_wage"], skills=skills_for(row["soc_code"]),
        ) for row in rows]


@mcp.tool()
async def get_occupation(soc_code: str, ctx: Context) -> Occupation:
    """One occupation by SOC code: title, projected growth, median wage, and its skill profile."""
    claims = caller(ctx)
    async with audited("get_occupation", claims, {"soc_code": soc_code}):
        rows = query("SELECT * FROM occupations WHERE soc_code = ?", soc_code)
        if not rows:
            raise UnknownOccupation(f"unknown SOC code {soc_code}")
        row = rows[0]
        return Occupation(
            soc_code=row["soc_code"], title=row["title"], growth_pct=row["growth_pct"],
            median_wage=row["median_wage"], skills=skills_for(row["soc_code"]),
        )


@mcp.tool()
async def get_program_occupation_map(ctx: Context) -> list[ProgramOccupation]:
    """The administrative crosswalk of program codes to occupation codes. It records which occupations a program was registered against; it is NOT evidence that a graduate's skills match one. Use it to find occupations no program maps to. To judge whether graduates would qualify, match get_course_outcomes skill tags against this occupation's skills instead."""
    claims = caller(ctx)
    async with audited("get_program_occupation_map", claims, {}):
        mapping: dict[str, list[str]] = {}
        for row in query("SELECT program_code, soc_code FROM program_occupation_map"
                         " ORDER BY program_code, soc_code"):
            mapping.setdefault(row["program_code"], []).append(row["soc_code"])
        return [ProgramOccupation(program_code=code, soc_codes=codes)
                for code, codes in sorted(mapping.items())]


app = BearerAuthMiddleware(mcp.streamable_http_app())
