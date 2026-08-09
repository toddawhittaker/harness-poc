"""mcp-colleague — fake SIS, real enforcement (SPEC §4.4).

The system of record. Colleague answers *what should happen next term*; Canvas
answers *what is happening this week*. That division is why both servers exist.

This server trusts nothing upstream. Every request re-validates the Bearer token
(mcp_auth.BearerAuthMiddleware) and every tool re-checks the caller's roles and
record assignments against that token (rules.py) — even when the orchestrator
has already done its own filtering, and especially when nothing upstream ran at
all, which is the bypass demo.
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
    UnknownStudent,
    audited,
    require_advisor_for_record,
    require_assignment,
    require_role,
)

DB_PATH = Path(os.environ.get("COLLEAGUE_DB_PATH", "/data/colleague.db"))

# "Quiet" means this many days since the last login, and it means it in both
# places this server counts it: the advisee roster's quiet_count and the dean's
# per-program percentage. One number, so an advisor's list and a dean's
# aggregate can never be describing different thresholds.
QUIET_AFTER_DAYS = 10

# Stateless, deliberately. Beyond scaling cleanly, it is what makes per-request
# authorization honest: a stateful session would let a tool run in the task
# opened by whoever sent the *first* request, so the identity a tool sees could
# outlive the request that carried it. See the long note in mcp_auth.py.
mcp = FastMCP("colleague", stateless_http=True, transport_security=TRANSPORT_SECURITY)

_lock = threading.Lock()
_db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
_db.row_factory = sqlite3.Row


def query(sql: str, *params: object) -> list[sqlite3.Row]:
    with _lock:
        return _db.execute(sql, params).fetchall()


# --------------------------------------------------------------------------
# Payloads. Typed returns give the model a schema instead of a wall of prose.
# --------------------------------------------------------------------------


class Advisee(BaseModel):
    student_id: str
    name: str
    program: str
    gpa: float
    last_login_days: int
    current_courses: list[str]
    term_grade_flags: list[str]


class AdviseeRoster(BaseModel):
    """The roster, with its size stated rather than left to be counted.

    A bare list makes the total something the reader works out, and the reader
    here is a language model that has repeatedly worked it out wrong — "your 24
    advisees" and "your 23 advisees" about the same 25 people. The count is
    computed from the same list it ships with, so the two cannot disagree.

    `flagged_count` and `quiet_count` are here for the same reason and one step
    further in. The total was the number the model got wrong first; once the
    total came from the tool it started getting the *subsets* wrong instead —
    "eight of your advisees have flags" written directly above a list of nine,
    three runs out of three. Those two subsets are the ones demo moment 1 opens
    with, they are the same two the seed guards, and neither is a matter of
    judgement: a flagged advisee is one with at least one term grade flag, and a
    quiet one has not logged in for more than QUIET_AFTER_DAYS days. Both are
    counted from the very rows this result ships, so a tally cannot disagree
    with the list beneath it.
    """

    advisee_count: int
    flagged_count: int
    quiet_count: int
    advisees: list[Advisee]


class StudentSummary(BaseModel):
    student_id: str
    name: str
    program: str
    gpa: float
    last_login_days: int
    credits_completed: int
    current_courses: list[str]
    term_grade_flags: list[str]


class ProgramSummary(BaseModel):
    program_code: str
    program_name: str
    headcount: int
    avg_gpa: float
    pct_quiet_over_10_days: float


class ProgramSummaries(BaseModel):
    """Per-program aggregates, with the number of programs stated.

    Same reason as AdviseeRoster: "none of the six programs" said two sentences
    after a tally of four is a sentence the model composed rather than read.
    """

    program_count: int
    programs: list[ProgramSummary]


class EnrollmentTrend(BaseModel):
    program_code: str
    term: str
    headcount: int


class RequirementProgress(BaseModel):
    course_code: str
    title: str
    credits: int
    sequence: int
    completed: bool
    in_progress: bool
    grade: str | None
    prereqs: list[str]
    prereqs_satisfied: bool


class DegreeProgress(BaseModel):
    student_id: str
    name: str
    program: str
    credits_completed: int
    credits_required: int
    requirements: list[RequirementProgress]


class NextTermOption(BaseModel):
    course_code: str
    title: str
    credits: int
    sequence: int
    prereqs: list[str]
    offered_next_term: bool
    seats: int | None
    # Why this course is open, in the tool's own words: the prerequisites that
    # were satisfied, with the term each was completed in and the grade. A
    # blocked option already states its blocker, so without this an open option
    # was the only thing in the result with no stated reason — and a model
    # reading silence as absence is what made demo moment 6 assert that a
    # completed prerequisite had not been completed. The licence is now stated
    # beside the option, from the same rows the eligibility test read.
    open_because: str


class NextTermOptions(BaseModel):
    student_id: str
    name: str
    program: str
    term: str
    options: list[NextTermOption]
    blocked: list[RequirementProgress]
    in_progress: list[str]


# --------------------------------------------------------------------------
# Reads. No authorization in here — that lives in the tools, above the data.
# --------------------------------------------------------------------------


def advisee_ids(advisor_sub: str) -> list[str]:
    return [row["student_id"] for row in
            query("SELECT student_id FROM advisor_assignments WHERE advisor_sub = ?", advisor_sub)]


def current_courses(student_id: str) -> list[str]:
    return [row["course_code"] for row in
            query("SELECT course_code FROM registrations WHERE student_id = ? ORDER BY course_code",
                  student_id)]


def grade_flags(student_id: str) -> list[str]:
    return [f"{row['course_code']}: {row['flag']}" for row in
            query("SELECT course_code, flag FROM term_grade_flags WHERE student_id = ?"
                  " ORDER BY course_code", student_id)]


def student_row(student_id: str) -> sqlite3.Row:
    rows = query("SELECT * FROM students WHERE id = ?", student_id)
    if not rows:
        # Reached only for an id that is genuinely absent. An id belonging to
        # another advisor is refused before it gets here, so this never doubles
        # as a way to probe which ids exist.
        raise UnknownStudent(f"unknown student id {student_id}")
    return rows[0]


def prereqs_for(course_code: str) -> list[str]:
    return [row["prereq_code"] for row in
            query("SELECT prereq_code FROM course_prereqs WHERE course_code = ? ORDER BY prereq_code",
                  course_code)]


def completed_grades(student_id: str) -> dict[str, tuple[str, str]]:
    """Course code → (term completed, grade), for everything already finished.

    The term comes along with the grade because `get_next_term_options` states
    why each option is open, and "CS-320 completed 2025SP (C)" is a fact an
    advisor can check against the transcript in front of them. Reading the
    grade without the term would make the sentence unverifiable.
    """
    return {row["course_code"]: (row["term"], row["grade"]) for row in
            query("SELECT course_code, term, grade FROM completed_courses WHERE student_id = ?",
                  student_id)}


def requirement_progress(student_id: str, program_code: str) -> list[RequirementProgress]:
    """Every required course, with what the student has done about it.

    Three states, not two. A course can be finished, currently being taken, or
    neither — and conflating the middle one with "neither" is what makes an
    advising tool recommend the courses the student is already sitting in.

    `prereqs_satisfied` still counts only *completed* courses. A prerequisite
    being taken right now is not yet met, and treating it as met would advise
    registering for the follow-on before the grade exists.
    """
    done = completed_grades(student_id)
    now = set(current_courses(student_id))
    rows = query(
        "SELECT r.course_code, r.sequence, r.credits, c.title"
        " FROM degree_requirements r LEFT JOIN courses c ON c.code = r.course_code"
        " WHERE r.program_code = ? ORDER BY r.sequence, r.course_code",
        program_code,
    )
    progress: list[RequirementProgress] = []
    for row in rows:
        prereqs = prereqs_for(row["course_code"])
        progress.append(RequirementProgress(
            course_code=row["course_code"],
            title=row["title"] or row["course_code"],
            credits=row["credits"],
            sequence=row["sequence"],
            completed=row["course_code"] in done,
            in_progress=row["course_code"] in now and row["course_code"] not in done,
            grade=done[row["course_code"]][1] if row["course_code"] in done else None,
            prereqs=prereqs,
            prereqs_satisfied=all(code in done for code in prereqs),
        ))
    return progress


def open_because(prereqs: list[str], done: dict[str, tuple[str, str]]) -> str:
    """The sentence a next-term option carries about why it is open.

    Only ever called for an option whose prereqs are all satisfied, so every
    code here is in `done`; a missing one would be a fault in the eligibility
    test above rather than something to paper over, and KeyError says so.
    """
    if not prereqs:
        return "open: no prerequisites"
    met = ", ".join(f"{code} completed {done[code][0]} ({done[code][1]})" for code in prereqs)
    return f"open: prereq{'s' if len(prereqs) > 1 else ''} {met}"


def next_term() -> str:
    rows = query("SELECT DISTINCT term FROM next_term_schedule ORDER BY term")
    return rows[0]["term"] if rows else "next term"


# --------------------------------------------------------------------------
# Liveness. No auth, no downstream calls — the middleware lets this path past.
# --------------------------------------------------------------------------


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: object) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# --------------------------------------------------------------------------
# Tools (SPEC §4.4).
# --------------------------------------------------------------------------


@mcp.tool()
async def get_my_advisees(ctx: Context) -> AdviseeRoster:
    """The advisees assigned to you, with current courses, GPA, days since last login, and any term grade flags. advisee_count is how many there are; flagged_count is how many carry at least one term grade flag; quiet_count is how many have not logged in for more than ten days."""
    claims = caller(ctx)
    async with audited("get_my_advisees", claims, {}):
        require_role(claims, "advisor", "get_my_advisees")
        advisees: list[Advisee] = []
        for student_id in advisee_ids(claims.sub):
            row = student_row(student_id)
            advisees.append(Advisee(
                student_id=row["id"],
                name=row["name"],
                program=row["program_code"],
                gpa=row["gpa"],
                last_login_days=row["last_login_days"],
                current_courses=current_courses(student_id),
                term_grade_flags=grade_flags(student_id),
            ))
        advisees.sort(key=lambda a: a.student_id)
        return AdviseeRoster(
            advisee_count=len(advisees),
            flagged_count=sum(1 for a in advisees if a.term_grade_flags),
            quiet_count=sum(1 for a in advisees if a.last_login_days > QUIET_AFTER_DAYS),
            advisees=advisees,
        )


@mcp.tool()
async def get_student_summary(student_id: str, ctx: Context) -> StudentSummary:
    """Record summary for one student: program, GPA, credits, current courses, days since last login, term grade flags."""
    claims = caller(ctx)
    async with audited("get_student_summary", claims, {"student_id": student_id}):
        require_advisor_for_record(claims, "get_student_summary")
        require_assignment(claims, student_id, advisee_ids(claims.sub))
        row = student_row(student_id)
        return StudentSummary(
            student_id=row["id"],
            name=row["name"],
            program=row["program_code"],
            gpa=row["gpa"],
            last_login_days=row["last_login_days"],
            credits_completed=row["credits_completed"],
            current_courses=current_courses(student_id),
            term_grade_flags=grade_flags(student_id),
        )


@mcp.tool()
async def get_program_summaries(ctx: Context) -> ProgramSummaries:
    """Per-program aggregates: headcount, average GPA, and the share of students who have not logged in for over ten days. program_count is how many programs there are."""
    claims = caller(ctx)
    async with audited("get_program_summaries", claims, {}):
        require_role(claims, "dean", "get_program_summaries")
        rows = query(
            "SELECT p.code, p.name, COUNT(s.id) AS headcount, AVG(s.gpa) AS avg_gpa,"
            " SUM(CASE WHEN s.last_login_days > ? THEN 1 ELSE 0 END) AS quiet"
            " FROM programs p LEFT JOIN students s ON s.program_code = p.code"
            " GROUP BY p.code, p.name ORDER BY p.code",
            QUIET_AFTER_DAYS,
        )
        programs = [ProgramSummary(
            program_code=row["code"],
            program_name=row["name"],
            headcount=row["headcount"] or 0,
            avg_gpa=round(row["avg_gpa"] or 0.0, 2),
            pct_quiet_over_10_days=round(100.0 * (row["quiet"] or 0) / row["headcount"], 1)
            if row["headcount"] else 0.0,
        ) for row in rows]
        return ProgramSummaries(program_count=len(programs), programs=programs)


@mcp.tool()
async def get_enrollment_trends(ctx: Context, program_code: str | None = None) -> list[EnrollmentTrend]:
    """Headcount by term for each program, or for one program if program_code is given."""
    claims = caller(ctx)
    async with audited("get_enrollment_trends", claims, {"program_code": program_code}):
        require_role(claims, "dean", "get_enrollment_trends")
        if program_code:
            rows = query("SELECT * FROM enrollment_trends WHERE program_code = ?"
                         " ORDER BY program_code, term", program_code)
        else:
            rows = query("SELECT * FROM enrollment_trends ORDER BY program_code, term")
        return [EnrollmentTrend(program_code=row["program_code"], term=row["term"],
                                headcount=row["headcount"]) for row in rows]


@mcp.tool()
async def get_student_degree_progress(student_id: str, ctx: Context) -> DegreeProgress:
    """Completed courses and credits against the student's program requirements, with prerequisites satisfied or not."""
    claims = caller(ctx)
    async with audited("get_student_degree_progress", claims, {"student_id": student_id}):
        require_advisor_for_record(claims, "get_student_degree_progress")
        require_assignment(claims, student_id, advisee_ids(claims.sub))
        row = student_row(student_id)
        requirements = requirement_progress(student_id, row["program_code"])
        return DegreeProgress(
            student_id=row["id"],
            name=row["name"],
            program=row["program_code"],
            credits_completed=row["credits_completed"],
            credits_required=sum(item.credits for item in requirements),
            requirements=requirements,
        )


@mcp.tool()
async def get_next_term_options(student_id: str, ctx: Context) -> NextTermOptions:
    """Remaining required courses whose prerequisites the student has met, flagged by which are offered next term. Each open option states in open_because which prerequisites were satisfied, with the term completed and the grade."""
    claims = caller(ctx)
    async with audited("get_next_term_options", claims, {"student_id": student_id}):
        require_advisor_for_record(claims, "get_next_term_options")
        require_assignment(claims, student_id, advisee_ids(claims.sub))
        row = student_row(student_id)
        term = next_term()
        done = completed_grades(student_id)
        offered = {schedule["course_code"]: schedule["seats"] for schedule in
                   query("SELECT course_code, seats FROM next_term_schedule WHERE term = ?", term)}

        options: list[NextTermOption] = []
        blocked: list[RequirementProgress] = []
        in_progress: list[str] = []
        for item in requirement_progress(student_id, row["program_code"]):
            if item.completed:
                continue
            if item.in_progress:
                # Being taken right now, so it is not a next-term option. Named
                # rather than dropped: "you are already covering these" is part
                # of the advising answer, and leaving them in `options` was
                # producing the recommendation to retake this term's courses.
                in_progress.append(item.course_code)
                continue
            if not item.prereqs_satisfied:
                # Carried separately rather than dropped: "why not this one" is
                # the advising conversation, and an advisor who only sees the
                # open doors cannot have it.
                blocked.append(item)
                continue
            options.append(NextTermOption(
                course_code=item.course_code,
                title=item.title,
                credits=item.credits,
                sequence=item.sequence,
                prereqs=item.prereqs,
                offered_next_term=item.course_code in offered,
                seats=offered.get(item.course_code),
                open_because=open_because(item.prereqs, done),
            ))
        return NextTermOptions(
            student_id=row["id"], name=row["name"], program=row["program_code"],
            term=term, options=options, blocked=blocked, in_progress=in_progress,
        )


app = BearerAuthMiddleware(mcp.streamable_http_app())
