#!/usr/bin/env python3
"""Deterministic fake data for harness-poc (SPEC §5).

Writes data/colleague.db, data/canvas.db, data/kuali.db, data/labor.db.
Idempotent: every run deletes and recreates all four.

The data is fake; the joins are real. One controlled vocabulary (SKILLS) feeds
both Kuali's course outcomes and Labor's occupation skills, so the qualification
and gap syntheses in the demo are exact-string matches rather than fuzzy vibes.

Run: uv run scripts/seed.py
"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

random.seed(398)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CURRENT_TERM = "2026FA"
NEXT_TERM = "2027SP"
PAST_TERMS = ["2024FA", "2025SP", "2025FA", "2026SP"]
TREND_TERMS = ["2025SP", "2025FA", "2026SP", "2026FA"]

# Advisor identities. `dana` matches the persona in config/personas.yaml; the
# other two are fictional and exist only to hold the other 275 advisees.
DANA = "dana"
OTHER_ADVISORS = [("adv-002", "Marcus Hale"), ("adv-003", "Rebecca Lin")]

# ---------------------------------------------------------------------------
# The controlled vocabulary. Kuali outcome tags and Labor occupation skills are
# both drawn from this list and from nowhere else.
# ---------------------------------------------------------------------------

SKILLS = [
    # security
    "network defense", "incident response", "threat intelligence",
    "vulnerability assessment", "penetration testing", "security architecture",
    "identity and access management", "cryptography", "risk assessment",
    "regulatory compliance", "security auditing", "digital forensics",
    # business
    "financial analysis", "financial reporting", "budgeting and forecasting",
    "project management", "strategic planning", "operations management",
    "marketing strategy", "business process analysis",
    # data
    "SQL", "data modeling", "data engineering", "statistical analysis",
    "machine learning", "deep learning", "data visualization",
    "predictive modeling", "experimental design",
    # infrastructure and software
    "cloud architecture", "infrastructure automation", "containerization",
    "systems administration", "network engineering", "software development",
    "algorithm design", "database administration", "API design",
    "distributed systems", "technical documentation",
    # health information
    "healthcare privacy", "medical coding", "health informatics",
    "revenue cycle management",
]

# These three are deliberately taught by NO program. They are what makes the
# gap analysis (demo moment 8) land: fast-growing occupations need them and the
# catalog cannot supply them. verify() asserts they stay untaught.
DELIBERATELY_UNTAUGHT = ["deep learning", "infrastructure automation", "containerization"]

# ---------------------------------------------------------------------------
# Programs and courses
# ---------------------------------------------------------------------------

PROGRAMS = [
    ("CS-BS", "Computer Science, BS", "11.0701", "bachelor"),
    ("IS-MS", "Information Systems, MS", "11.0401", "master"),
    ("CYB-BS", "Cybersecurity, BS", "11.1003", "bachelor"),
    ("DAT-MS", "Data Analytics, MS", "30.7101", "master"),
    ("BUS-BS", "Business Administration, BS", "52.0201", "bachelor"),
    ("HIM-BS", "Health Information Management, BS", "51.0706", "bachelor"),
]

# program -> ordered required sequence of (code, title, credits, prereqs, outcome skills)
CURRICULUM: dict[str, list[tuple[str, str, int, list[str], list[str]]]] = {
    "CS-BS": [
        ("CS-101", "Introduction to Programming", 3, [],
         ["software development", "algorithm design", "technical documentation"]),
        ("CS-201", "Data Structures", 3, ["CS-101"],
         ["algorithm design", "software development", "data modeling"]),
        ("CS-210", "Discrete Mathematics", 3, [],
         ["algorithm design", "statistical analysis"]),
        ("CS-310", "Algorithms", 3, ["CS-201"],
         ["algorithm design", "distributed systems", "software development"]),
        ("CS-320", "Database Systems", 3, ["CS-201"],
         ["SQL", "database administration", "data modeling"]),
        ("CS-350", "Software Engineering", 3, ["CS-201"],
         ["software development", "API design", "project management", "technical documentation"]),
        ("CS-410", "Cloud Architecture", 3, ["CS-320"],
         ["cloud architecture", "distributed systems", "API design", "systems administration"]),
        ("CS-460", "Computer Science Capstone", 3, ["CS-310", "CS-350"],
         ["software development", "project management", "technical documentation"]),
    ],
    "IS-MS": [
        ("IS-500", "Information Systems Management", 3, [],
         ["project management", "business process analysis", "strategic planning"]),
        ("IS-520", "Enterprise Architecture", 3, ["IS-500"],
         ["security architecture", "systems administration", "business process analysis"]),
        ("IS-540", "IT Project Management", 3, ["IS-500"],
         ["project management", "budgeting and forecasting", "technical documentation"]),
        ("IS-610", "Data Governance", 3, ["IS-520"],
         ["regulatory compliance", "data modeling", "risk assessment"]),
        ("IS-620", "Cloud Systems", 3, ["IS-520"],
         ["cloud architecture", "systems administration", "network engineering", "API design"]),
        ("IS-700", "Information Systems Capstone", 3, ["IS-610", "IS-620"],
         ["project management", "strategic planning", "technical documentation"]),
    ],
    "CYB-BS": [
        ("CYB-110", "Foundations of Cybersecurity", 3, [],
         ["risk assessment", "regulatory compliance", "technical documentation"]),
        ("CYB-210", "Network Defense", 3, ["CYB-110"],
         ["network defense", "network engineering", "systems administration"]),
        ("CYB-240", "Operating Systems Security", 3, ["CYB-110"],
         ["systems administration", "vulnerability assessment", "identity and access management"]),
        ("CYB-310", "Threat Detection and Response", 3, ["CYB-210"],
         ["threat intelligence", "incident response", "network defense", "digital forensics"]),
        ("CYB-330", "Applied Cryptography", 3, ["CYB-240"],
         ["cryptography", "identity and access management"]),
        ("CYB-410", "Security Architecture", 3, ["CYB-310"],
         ["security architecture", "identity and access management", "risk assessment"]),
        ("CYB-420", "Governance, Risk, and Compliance", 3, ["CYB-310"],
         ["regulatory compliance", "security auditing", "risk assessment"]),
        ("CYB-460", "Cybersecurity Capstone", 3, ["CYB-410", "CYB-420"],
         ["penetration testing", "vulnerability assessment", "incident response", "technical documentation"]),
    ],
    "DAT-MS": [
        ("DAT-500", "Foundations of Data Analytics", 3, [],
         ["data modeling", "SQL", "statistical analysis"]),
        ("DAT-510", "Statistical Methods", 3, ["DAT-500"],
         ["statistical analysis", "experimental design", "predictive modeling"]),
        ("DAT-520", "Data Engineering", 3, ["DAT-500"],
         ["data engineering", "SQL", "data modeling", "database administration"]),
        ("DAT-610", "Machine Learning", 3, ["DAT-510"],
         ["machine learning", "predictive modeling", "experimental design"]),
        ("DAT-620", "Data Visualization", 3, ["DAT-510"],
         ["data visualization", "technical documentation"]),
        ("DAT-700", "Data Analytics Capstone", 3, ["DAT-610", "DAT-620"],
         ["machine learning", "data visualization", "project management"]),
    ],
    "BUS-BS": [
        ("BUS-101", "Principles of Management", 3, [],
         ["strategic planning", "project management", "business process analysis"]),
        ("BUS-150", "Financial Accounting", 3, [],
         ["financial reporting", "financial analysis"]),
        ("BUS-201", "Business Analytics", 3, ["BUS-150"],
         ["SQL", "data visualization", "statistical analysis", "business process analysis"]),
        ("BUS-230", "Principles of Marketing", 3, [],
         ["marketing strategy", "business process analysis"]),
        ("BUS-310", "Corporate Finance", 3, ["BUS-150"],
         ["financial analysis", "budgeting and forecasting"]),
        ("BUS-330", "Operations Management", 3, ["BUS-201"],
         ["operations management", "business process analysis", "project management"]),
        ("BUS-410", "Strategic Management", 3, ["BUS-310"],
         ["strategic planning", "financial analysis", "risk assessment"]),
        ("BUS-460", "Business Capstone", 3, ["BUS-410"],
         ["strategic planning", "project management", "technical documentation"]),
    ],
    "HIM-BS": [
        ("HIM-110", "Health Information Systems", 3, [],
         ["health informatics", "technical documentation"]),
        ("HIM-210", "Medical Coding", 3, ["HIM-110"],
         ["medical coding", "regulatory compliance"]),
        ("HIM-240", "Healthcare Privacy and Compliance", 3, ["HIM-110"],
         ["healthcare privacy", "regulatory compliance", "risk assessment"]),
        ("HIM-310", "Health Data Analytics", 3, ["HIM-210"],
         ["health informatics", "SQL", "data visualization", "statistical analysis"]),
        ("HIM-340", "Revenue Cycle Management", 3, ["HIM-210"],
         ["revenue cycle management", "financial analysis"]),
        ("HIM-410", "Informatics Leadership", 3, ["HIM-310"],
         ["health informatics", "project management", "strategic planning"]),
        ("HIM-460", "Health Information Capstone", 3, ["HIM-410"],
         ["health informatics", "technical documentation", "project management"]),
    ],
}

# Courses offered next term. Deliberately not everything — "is it offered?" has
# to be a real question for get_next_term_options to be worth calling.
NEXT_TERM_OFFERED = {
    "CS-101", "CS-201", "CS-310", "CS-320", "CS-350", "CS-410",
    "IS-500", "IS-520", "IS-540", "IS-620",
    "CYB-110", "CYB-210", "CYB-240", "CYB-310", "CYB-410", "CYB-420",
    "DAT-500", "DAT-510", "DAT-520", "DAT-610", "DAT-620",
    "BUS-101", "BUS-150", "BUS-201", "BUS-230", "BUS-310", "BUS-330",
    "HIM-110", "HIM-210", "HIM-240", "HIM-310", "HIM-340",
}

# ---------------------------------------------------------------------------
# Labor market
# ---------------------------------------------------------------------------

# What "fast-growing" means when demo moment 7 asks for it. Six of the twelve
# occupations sit above this line; the trio the qualification synthesis needs
# must all be among them, which is what verify() checks.
FAST_GROWING_MIN_PCT = 20.0

# (soc_code, title, growth_pct, median_wage, skills)
OCCUPATIONS = [
    ("15-2099", "AI/ML Engineers", 35.2, 136620,
     ["machine learning", "deep learning", "predictive modeling", "statistical analysis",
      "software development", "data modeling", "distributed systems"]),
    ("15-1241", "Cloud Infrastructure Architects", 33.8, 130390,
     ["cloud architecture", "infrastructure automation", "containerization",
      "systems administration", "network engineering", "distributed systems", "API design"]),
    ("15-1212", "Information Security Analysts", 32.7, 120360,
     ["network defense", "incident response", "threat intelligence", "vulnerability assessment",
      "security architecture", "risk assessment", "regulatory compliance", "security auditing"]),
    ("15-2051", "Data Scientists", 28.4, 108020,
     ["statistical analysis", "machine learning", "data visualization", "SQL",
      "predictive modeling", "experimental design", "data modeling"]),
    ("11-9111", "Medical and Health Services Managers", 24.1, 110680,
     ["health informatics", "regulatory compliance", "project management",
      "budgeting and forecasting", "operations management"]),
    ("15-1252", "Software Developers", 17.9, 132270,
     ["software development", "algorithm design", "API design", "technical documentation",
      "distributed systems", "project management"]),
    ("11-3021", "Computer and Information Systems Managers", 15.4, 169510,
     ["strategic planning", "project management", "budgeting and forecasting",
      "security architecture", "business process analysis"]),
    ("13-1111", "Management Analysts", 10.6, 99410,
     ["business process analysis", "strategic planning", "financial analysis",
      "project management", "data visualization"]),
    ("15-1211", "Computer Systems Analysts", 10.4, 103800,
     ["business process analysis", "systems administration", "data modeling",
      "technical documentation", "project management"]),
    ("29-2072", "Medical Records Specialists", 8.6, 48780,
     ["medical coding", "healthcare privacy", "regulatory compliance",
      "health informatics", "revenue cycle management"]),
    ("13-2051", "Financial Analysts", 8.2, 99890,
     ["financial analysis", "financial reporting", "budgeting and forecasting",
      "strategic planning", "data visualization", "SQL"]),
    # 21.5% is a demo constraint, not an observation. Demo moment 7 asks about
    # *fast-growing* occupations, so a partial match parked at 3.1% is filtered
    # out by the question itself and the strong/partial/miss trio collapses to a
    # single strong match. verify() now checks the trio inside the fast-growing
    # band rather than across all twelve, so this cannot silently regress.
    ("15-1244", "Network and Computer Systems Administrators", 21.5, 95360,
     ["systems administration", "network engineering", "infrastructure automation",
      "containerization", "technical documentation", "cloud architecture"]),
]

# Every program maps to at least one occupation. AI/ML Engineers and Cloud
# Infrastructure Architects appear nowhere — they are the gap.
PROGRAM_OCCUPATION_MAP = [
    ("CS-BS", "15-1252"), ("CS-BS", "15-2051"), ("CS-BS", "15-1211"),
    ("IS-MS", "15-1211"), ("IS-MS", "11-3021"), ("IS-MS", "15-1244"),
    ("CYB-BS", "15-1212"), ("CYB-BS", "15-1244"),
    ("DAT-MS", "15-2051"), ("DAT-MS", "13-1111"),
    ("BUS-BS", "13-2051"), ("BUS-BS", "13-1111"), ("BUS-BS", "11-3021"),
    ("HIM-BS", "29-2072"), ("HIM-BS", "11-9111"),
]

# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Aaron", "Alicia", "Amanda", "Andre", "Angela", "Anthony", "Bethany", "Brandon",
    "Brianna", "Caleb", "Carmen", "Chelsea", "Christopher", "Daniel", "Danielle",
    "Derek", "Diana", "Elena", "Elliot", "Emily", "Eric", "Felicia", "Gabriel",
    "Grace", "Gregory", "Hannah", "Ian", "Isabel", "Jacob", "Jasmine", "Jeffrey",
    "Jenna", "Jonathan", "Julia", "Karen", "Kevin", "Krista", "Lauren", "Leon",
    "Lucas", "Marcus", "Maria", "Megan", "Micah", "Nathan", "Nicole", "Olivia",
    "Patrick", "Priya", "Rachel", "Ramon", "Renee", "Robert", "Samuel", "Sara",
    "Sean", "Simone", "Stephanie", "Terrence", "Theresa", "Tyler", "Vanessa",
    "Victor", "Wesley", "Yolanda", "Zachary",
]

LAST_NAMES = [
    "Abbott", "Alvarez", "Bennett", "Boyd", "Bradley", "Bryant", "Chan", "Cline",
    "Coleman", "Cortez", "Dawson", "Delgado", "Doyle", "Ellis", "Ferguson",
    "Fletcher", "Foley", "Gallagher", "Gibson", "Glover", "Hammond", "Harper",
    "Hendricks", "Hoffman", "Ingram", "Jensen", "Kaur", "Keller", "Kim", "Larsen",
    "Lawson", "Leblanc", "Lombardi", "Maldonado", "Marsh", "McBride", "Mercer",
    "Novak", "Odell", "Osborne", "Padilla", "Pham", "Quinn", "Ramsey", "Rhodes",
    "Rivas", "Sandoval", "Schroeder", "Sharma", "Sheppard", "Sorensen", "Stanton",
    "Tate", "Underwood", "Valdez", "Vaughn", "Walsh", "Weaver", "Whitfield",
    "Wilkerson", "Yates", "Zamora",
]

N_STUDENTS = 300
FIRST_STUDENT_ID = 1001

# Dana advises a block with S-1044 deliberately punched out of the middle, and
# S-1042 inside it because demo moment 6 asks about that student by name.
#
# The hole is load-bearing, not untidiness. S-1044 is a real, seeded student in
# the middle of dana's id range who belongs to another advisor, which is what
# makes the SPEC §4.4 refusal — "Student S-1044 is not among your assigned
# advisees" — an authorization boundary rather than a "no such student" answer.
# A contiguous block leaves nothing to ask about. Do not close the gap.
DANA_ADVISEE_IDS = [f"S-{n}" for n in range(1030, 1056) if n != 1044]  # 25 students
NOT_DANAS_ADVISEE = "S-1044"

# The eight quiet ones. Demo moment 1 depends on this tail existing and being
# small enough to name out loud.
DANA_QUIET_IDS = ["S-1031", "S-1035", "S-1038", "S-1043", "S-1047", "S-1049", "S-1052", "S-1054"]

# Hand-tuned transcripts, so the next-term answers are crisp instead of mushy.
# Everyone else's completed courses are generated.
HANDMADE_TRANSCRIPTS: dict[str, tuple[str, list[str]]] = {
    # (program, completed course codes)
    "S-1042": ("CYB-BS", ["CYB-110", "CYB-210", "CYB-240", "CYB-330", "CYB-310"]),
    "S-1036": ("CS-BS", ["CS-101", "CS-201", "CS-210", "CS-320"]),
    "S-1045": ("DAT-MS", ["DAT-500", "DAT-510"]),
    # The blocked one: wants Corporate Finance, has not taken Financial Accounting.
    "S-1049": ("BUS-BS", ["BUS-101", "BUS-230"]),
}

# The student demo moment 6 asks about. Kept separate from HANDMADE_TRANSCRIPTS
# on purpose, and the purpose is not style.
#
# HANDMADE_TRANSCRIPTS is consulted inside make_students, where a handmade entry
# skips the random.choice that picks a program. Adding one there moves every
# later draw in the stream — including the loop that re-draws last_login for all
# of dana's advisees — which would change S-1042's record. Session 2 decided
# S-1042's record must not move: he is legitimately near the end of his program,
# and bending a real answer to fit a slide is the one dishonest thing a demo
# about honest answers cannot do. So the pin is applied later, in seed_colleague,
# where it disturbs only students seeded after this one.
#
# S-1055 is a CS-BS student in dana's block with a 3.41 GPA who logged in three
# days ago — no flags, nothing to distract from the question being asked. With
# CS-101, CS-201 and CS-320 behind him and CS-210 in progress, next term offers
# three courses he can actually take and exactly one he cannot:
#
#   options   CS-310 Algorithms          (prereq CS-201, met)
#             CS-350 Software Engineering (prereq CS-201, met)
#             CS-410 Cloud Architecture   (prereq CS-320, met)
#   blocked   CS-460 Capstone             (needs CS-310 and CS-350 first)
#
# student_id -> (completed course codes, current-term registrations)
STEP_6_STUDENT = "S-1055"
PINNED_PROGRESS: dict[str, tuple[list[str], list[str]]] = {
    STEP_6_STUDENT: (["CS-101", "CS-201", "CS-320"], ["CS-210"]),
}

# Canvas sections. noor teaches CYB-310-A and CYB-210-A; BUS-201-A belongs to
# someone else, which is what makes the SPEC §4.6 refusal message true.
#
# Noor holds no BUS section at all, and that is deliberate. She used to teach
# BUS-201-B — one character from BUS-201-A, the section demo moment 5 asks her
# about and expects her to be refused for. The model lists her sections first,
# finds a near-identical id it IS allowed to read, and helpfully answers about
# that instead: the tool refusal never fires and the amber row demo moment 9
# points at is never written. That is a name collision the seed created, not
# model whimsy, so the seed is where it is fixed. `verify` asserts it.
SECTIONS = [
    ("CYB-310-A", "CYB-310", "noor", "Noor Haddad"),
    ("CYB-310-B", "CYB-310", "fac-004", "Alan Petrov"),
    ("BUS-201-A", "BUS-201", "fac-005", "Denise Crawford"),
    ("BUS-201-B", "BUS-201", "fac-005", "Denise Crawford"),
    ("CS-201-A", "CS-201", "fac-006", "Harold Nguyen"),
    ("CS-320-A", "CS-320", "fac-006", "Harold Nguyen"),
    ("CYB-210-A", "CYB-210", "noor", "Noor Haddad"),
    ("CYB-240-A", "CYB-240", "fac-004", "Alan Petrov"),
    ("DAT-510-A", "DAT-510", "fac-007", "Ingrid Solberg"),
    ("DAT-520-A", "DAT-520", "fac-007", "Ingrid Solberg"),
    ("IS-520-A", "IS-520", "fac-008", "Paul Achebe"),
    ("BUS-310-A", "BUS-310", "fac-005", "Denise Crawford"),
    ("HIM-210-A", "HIM-210", "fac-009", "Tamara Whitlock"),
    ("HIM-310-A", "HIM-310", "fac-009", "Tamara Whitlock"),
    ("CS-101-A", "CS-101", "fac-006", "Harold Nguyen"),
    ("HIM-110-A", "HIM-110", "fac-009", "Tamara Whitlock"),
    ("IS-500-A", "IS-500", "fac-008", "Paul Achebe"),
    ("DAT-500-A", "DAT-500", "fac-007", "Ingrid Solberg"),
    ("BUS-101-A", "BUS-101", "fac-005", "Denise Crawford"),
    ("CYB-110-A", "CYB-110", "fac-004", "Alan Petrov"),
]

OUTCOME_TEMPLATES = [
    "Apply {skill} to problems encountered in {title}.",
    "Evaluate {skill} practices in a {title} context.",
    "Demonstrate {skill} using the tools introduced in {title}.",
    "Analyze scenarios from {title} that require {skill}.",
    "Communicate {title} findings that depend on {skill}.",
]

GRADE_FLAG_TEXT = [
    "D at midterm",
    "missing 3 assignments",
    "no submissions in 2 weeks",
    "withdrew from a co-requisite",
    "incomplete carried from prior term",
]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def course_index() -> dict[str, tuple[str, str, int, list[str]]]:
    """code -> (program_code, title, credits, prereqs)."""
    index: dict[str, tuple[str, str, int, list[str]]] = {}
    for program_code, courses in CURRICULUM.items():
        for code, title, credits, prereqs, _skills in courses:
            index[code] = (program_code, title, credits, prereqs)
    return index


COURSES = course_index()


def make_students() -> list[dict]:
    """300 students with boring realistic names and a plausible spread."""
    pairs = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
    random.shuffle(pairs)
    program_codes = [p[0] for p in PROGRAMS]

    students: list[dict] = []
    for i in range(N_STUDENTS):
        sid = f"S-{FIRST_STUDENT_ID + i}"
        first, last = pairs[i]
        program = HANDMADE_TRANSCRIPTS.get(sid, (None, None))[0] or random.choice(program_codes)

        gpa = round(min(4.0, max(1.6, random.gauss(3.15, 0.45))), 2)
        # Mostly current; a thin tail of quiet students across the population so
        # the dean's "% inactive" aggregate is not zero.
        last_login = random.choices(
            [random.randint(0, 5), random.randint(6, 9), random.randint(10, 26)],
            weights=[78, 16, 6],
        )[0]

        students.append({
            "id": sid,
            "name": f"{first} {last}",
            "program_code": program,
            "gpa": gpa,
            "last_login_days": last_login,
        })

    by_id = {s["id"]: s for s in students}

    # The demo depends on exactly eight of dana's advisees being quiet, and on
    # the rest of her list being visibly fine.
    for sid in DANA_ADVISEE_IDS:
        by_id[sid]["last_login_days"] = random.randint(0, 5)
    for n, sid in enumerate(DANA_QUIET_IDS):
        by_id[sid]["last_login_days"] = 11 + n * 2
        by_id[sid]["gpa"] = round(min(2.9, max(1.6, random.gauss(2.35, 0.35))), 2)

    for sid, (program, _completed) in HANDMADE_TRANSCRIPTS.items():
        by_id[sid]["program_code"] = program

    return students


def completed_for(student: dict) -> list[str]:
    """Which required courses this student has already passed."""
    handmade = HANDMADE_TRANSCRIPTS.get(student["id"])
    if handmade:
        return list(handmade[1])

    sequence = [c[0] for c in CURRICULUM[student["program_code"]]]
    # Progress through the sequence in order, so prereq chains stay coherent.
    taken = random.randint(0, len(sequence) - 2)
    return sequence[:taken]


def prereqs_met(code: str, completed: set[str]) -> bool:
    return all(p in completed for p in COURSES[code][3])


def eligible_next(program_code: str, completed: set[str]) -> list[str]:
    """Remaining required courses whose prereqs are satisfied."""
    return [
        code for code, _t, _c, _p, _s in CURRICULUM[program_code]
        if code not in completed and prereqs_met(code, completed)
    ]


def fresh_db(name: str) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


# ---------------------------------------------------------------------------
# colleague.db — the record
# ---------------------------------------------------------------------------


def seed_colleague(students: list[dict]) -> dict[str, dict]:
    conn = fresh_db("colleague.db")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE programs (
            code TEXT PRIMARY KEY, name TEXT, cip_code TEXT, degree_level TEXT);
        CREATE TABLE courses (
            code TEXT PRIMARY KEY, program_code TEXT, title TEXT, credits INTEGER);
        CREATE TABLE course_prereqs (course_code TEXT, prereq_code TEXT);
        CREATE TABLE degree_requirements (
            program_code TEXT, course_code TEXT, sequence INTEGER, credits INTEGER);
        CREATE TABLE students (
            id TEXT PRIMARY KEY, name TEXT, program_code TEXT, gpa REAL,
            last_login_days INTEGER, credits_completed INTEGER);
        CREATE TABLE advisor_assignments (advisor_sub TEXT, advisor_name TEXT, student_id TEXT);
        CREATE TABLE completed_courses (
            student_id TEXT, course_code TEXT, term TEXT, grade TEXT, credits INTEGER);
        CREATE TABLE registrations (student_id TEXT, course_code TEXT, term TEXT);
        CREATE TABLE term_grade_flags (student_id TEXT, course_code TEXT, flag TEXT);
        CREATE TABLE next_term_schedule (course_code TEXT, term TEXT, seats INTEGER);
        CREATE TABLE enrollment_trends (program_code TEXT, term TEXT, headcount INTEGER);
    """)

    c.executemany("INSERT INTO programs VALUES (?,?,?,?)", PROGRAMS)

    for program_code, courses in CURRICULUM.items():
        for seq, (code, title, credits, prereqs, _skills) in enumerate(courses, start=1):
            c.execute("INSERT INTO courses VALUES (?,?,?,?)", (code, program_code, title, credits))
            c.execute("INSERT INTO degree_requirements VALUES (?,?,?,?)",
                      (program_code, code, seq, credits))
            for prereq in prereqs:
                c.execute("INSERT INTO course_prereqs VALUES (?,?)", (code, prereq))

    for code in sorted(NEXT_TERM_OFFERED):
        c.execute("INSERT INTO next_term_schedule VALUES (?,?,?)",
                  (code, NEXT_TERM, random.randint(18, 40)))

    # Advisor assignments: dana's 25, the rest split between two fictional advisors.
    remaining = [s["id"] for s in students if s["id"] not in set(DANA_ADVISEE_IDS)]
    random.shuffle(remaining)
    half = len(remaining) // 2
    assignments = [(DANA, "Dana Whitfield", sid) for sid in DANA_ADVISEE_IDS]
    assignments += [(OTHER_ADVISORS[0][0], OTHER_ADVISORS[0][1], sid) for sid in remaining[:half]]
    assignments += [(OTHER_ADVISORS[1][0], OTHER_ADVISORS[1][1], sid) for sid in remaining[half:]]
    c.executemany("INSERT INTO advisor_assignments VALUES (?,?,?)", assignments)

    state: dict[str, dict] = {}
    for student in students:
        pinned = PINNED_PROGRESS.get(student["id"])
        # Drawn either way, then overridden. Skipping the draw for a pinned
        # student would resequence every student seeded before this one too.
        completed = completed_for(student)
        if pinned:
            completed = list(pinned[0])
        credits = sum(COURSES[code][2] for code in completed)
        c.execute("INSERT INTO students VALUES (?,?,?,?,?,?)",
                  (student["id"], student["name"], student["program_code"],
                   student["gpa"], student["last_login_days"], credits))

        for n, code in enumerate(completed):
            grade = random.choices(["A", "B", "C", "D"], weights=[30, 42, 22, 6])[0]
            term = PAST_TERMS[min(n // 2, len(PAST_TERMS) - 1)]
            c.execute("INSERT INTO completed_courses VALUES (?,?,?,?,?)",
                      (student["id"], code, term, grade, COURSES[code][2]))

        # Current registrations come from what they are actually eligible for.
        # Sample rather than take the first N: taking the head of the sequence
        # starves later courses, and the demo needs CYB-310 and BUS-201 full
        # enough to talk about.
        eligible = eligible_next(student["program_code"], set(completed))
        current = random.sample(eligible, min(random.randint(1, 3), len(eligible)))
        if pinned:
            current = list(pinned[1])
        for code in current:
            c.execute("INSERT INTO registrations VALUES (?,?,?)",
                      (student["id"], code, CURRENT_TERM))

        # Struggling students carry visible flags — this is what "seem to be
        # struggling" resolves to when the advisor asks.
        if student["last_login_days"] > 10 or student["gpa"] < 2.5:
            for code in current[:2]:
                c.execute("INSERT INTO term_grade_flags VALUES (?,?,?)",
                          (student["id"], code, random.choice(GRADE_FLAG_TEXT)))

        state[student["id"]] = {**student, "completed": completed, "current": current}

    # Four terms of headcounts per program, trending gently.
    for code, _name, _cip, _level in PROGRAMS:
        base = sum(1 for s in students if s["program_code"] == code)
        for n, term in enumerate(TREND_TERMS):
            drift = round(base * (0.90 + 0.035 * n)) + random.randint(-3, 3)
            c.execute("INSERT INTO enrollment_trends VALUES (?,?,?)", (code, term, max(1, drift)))

    conn.commit()
    conn.close()
    return state


# ---------------------------------------------------------------------------
# canvas.db — the pulse
# ---------------------------------------------------------------------------


def seed_canvas(state: dict[str, dict]) -> None:
    conn = fresh_db("canvas.db")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE sections (
            id TEXT PRIMARY KEY, course_code TEXT, program_code TEXT,
            instructor_sub TEXT, instructor_name TEXT, term TEXT);
        CREATE TABLE faculty_assignments (instructor_sub TEXT, section_id TEXT);
        CREATE TABLE section_enrollment (section_id TEXT, student_id TEXT, student_name TEXT);
        CREATE TABLE activity (
            section_id TEXT, student_id TEXT, last_login_days INTEGER,
            submitted INTEGER, missing INTEGER);
    """)

    sections_by_course: dict[str, list[str]] = {}
    for section_id, course_code, sub, name in SECTIONS:
        program_code = COURSES[course_code][0]
        c.execute("INSERT INTO sections VALUES (?,?,?,?,?,?)",
                  (section_id, course_code, program_code, sub, name, CURRENT_TERM))
        c.execute("INSERT INTO faculty_assignments VALUES (?,?)", (sub, section_id))
        sections_by_course.setdefault(course_code, []).append(section_id)

    # Enroll each student in sections of the courses they are registered for,
    # keyed to the SAME student ids as colleague so cross-source joins are real.
    fill_counter: dict[str, int] = {code: 0 for code in sections_by_course}
    for student in state.values():
        for course_code in student["current"]:
            options = sections_by_course.get(course_code)
            if not options:
                continue
            # Round-robin across a course's sections so both sections of a
            # two-section course fill evenly.
            section_id = options[fill_counter[course_code] % len(options)]
            fill_counter[course_code] += 1
            c.execute("INSERT INTO section_enrollment VALUES (?,?,?)",
                      (section_id, student["id"], student["name"]))

            base = student["last_login_days"]
            if section_id == "CYB-310-A":
                # Visibly healthy: noor's own-section answer should have texture.
                login = random.randint(0, 3)
                missing = random.choices([0, 1, 2], weights=[70, 25, 5])[0]
            elif section_id == "BUS-201-B":
                # Visibly not.
                login = random.choices([random.randint(0, 4), random.randint(7, 20)],
                                       weights=[20, 80])[0]
                missing = random.randint(3, 6)
            else:
                login = max(0, base + random.randint(-2, 2))
                missing = random.choices([0, 1, 2, 3], weights=[55, 25, 13, 7])[0]

            submitted = max(0, 8 - missing)
            c.execute("INSERT INTO activity VALUES (?,?,?,?,?)",
                      (section_id, student["id"], login, submitted, missing))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# kuali.db — the curriculum
# ---------------------------------------------------------------------------


def seed_kuali() -> None:
    conn = fresh_db("kuali.db")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE programs (code TEXT PRIMARY KEY, name TEXT, cip_code TEXT);
        CREATE TABLE curriculum (
            program_code TEXT, course_code TEXT, title TEXT, credits INTEGER,
            sequence INTEGER, prereqs TEXT);
        CREATE TABLE outcomes (
            program_code TEXT, course_code TEXT, outcome_id TEXT, text TEXT, skill TEXT);
    """)

    for code, name, cip, _level in PROGRAMS:
        c.execute("INSERT INTO programs VALUES (?,?,?)", (code, name, cip))

    template_n = 0
    for program_code, courses in CURRICULUM.items():
        for seq, (code, title, credits, prereqs, skills) in enumerate(courses, start=1):
            c.execute("INSERT INTO curriculum VALUES (?,?,?,?,?,?)",
                      (program_code, code, title, credits, seq, ",".join(prereqs)))
            for n, skill in enumerate(skills, start=1):
                text = OUTCOME_TEMPLATES[template_n % len(OUTCOME_TEMPLATES)].format(
                    skill=skill, title=title)
                template_n += 1
                c.execute("INSERT INTO outcomes VALUES (?,?,?,?,?)",
                          (program_code, code, f"{code}-O{n}", text, skill))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# labor.db — the market
# ---------------------------------------------------------------------------


def seed_labor() -> None:
    conn = fresh_db("labor.db")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE occupations (
            soc_code TEXT PRIMARY KEY, title TEXT, growth_pct REAL, median_wage INTEGER);
        CREATE TABLE occupation_skills (soc_code TEXT, skill TEXT);
        CREATE TABLE program_occupation_map (program_code TEXT, soc_code TEXT);
    """)

    for soc, title, growth, wage, skills in OCCUPATIONS:
        c.execute("INSERT INTO occupations VALUES (?,?,?,?)", (soc, title, growth, wage))
        for skill in skills:
            c.execute("INSERT INTO occupation_skills VALUES (?,?)", (soc, skill))

    c.executemany("INSERT INTO program_occupation_map VALUES (?,?)", PROGRAM_OCCUPATION_MAP)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Verification — the demo depends on these being true, so fail loudly now
# ---------------------------------------------------------------------------


def taught_skills() -> dict[str, set[str]]:
    """program_code -> the set of skills its outcomes cover."""
    return {
        program_code: {skill for _c, _t, _cr, _p, skills in courses for skill in skills}
        for program_code, courses in CURRICULUM.items()
    }


def next_term_shape(student: dict) -> tuple[list[str], list[str], list[str]]:
    """(open, blocked, in progress) — the three lists get_next_term_options returns.

    Kept in step with services/mcp-colleague/app.py::get_next_term_options: a
    course being taken this term is neither an option nor a blocker, and a
    prerequisite in progress is not yet met.
    """
    completed = set(student["completed"])
    now = set(student["current"])
    options, blocked, in_progress = [], [], []
    for code, _title, _credits, prereqs, _skills in CURRICULUM[student["program_code"]]:
        if code in completed:
            continue
        if code in now:
            in_progress.append(code)
        elif all(prereq in completed for prereq in prereqs):
            options.append(code)
        else:
            blocked.append(code)
    return options, blocked, in_progress


def verify(state: dict[str, dict]) -> None:
    taught = taught_skills()
    all_taught = set().union(*taught.values())

    for skill in {s for _c, _t, _cr, _p, sk in
                  [c for cs in CURRICULUM.values() for c in cs] for s in sk}:
        assert skill in SKILLS, f"outcome skill {skill!r} is not in the controlled vocabulary"
    for _soc, title, _g, _w, skills in OCCUPATIONS:
        for skill in skills:
            assert skill in SKILLS, f"{title} skill {skill!r} is not in the controlled vocabulary"

    dana_advisees = [state[sid] for sid in DANA_ADVISEE_IDS]
    assert len(dana_advisees) == 25, "dana must advise exactly 25 students"
    quiet = [s for s in dana_advisees if s["last_login_days"] > 10]
    assert len(quiet) == 8, f"expected 8 quiet advisees for dana, got {len(quiet)}"

    # The RBAC refusal needs a seeded student inside dana's id range who is not
    # hers, or the test proves "no such student" instead of "not your advisee".
    numbers = sorted(int(sid.split("-")[1]) for sid in DANA_ADVISEE_IDS)
    assert numbers != list(range(numbers[0], numbers[-1] + 1)), (
        "dana's advisee ids are contiguous; there is no seeded non-advisee to "
        "ask about, and the SPEC §4.4 refusal test cannot tell an authorization "
        "boundary from a missing record"
    )
    assert NOT_DANAS_ADVISEE in state, f"{NOT_DANAS_ADVISEE} must be a real student"
    assert NOT_DANAS_ADVISEE not in set(DANA_ADVISEE_IDS), (
        f"{NOT_DANAS_ADVISEE} must belong to another advisor"
    )

    # Demo moment 6 asks one advisee what to take next term. The answer is only
    # worth putting on a projector if it has open doors AND a closed one, so
    # both halves are asserted the way get_next_term_options computes them:
    # a course being taken right now is neither an option nor a blocker.
    step6 = state[STEP_6_STUDENT]
    assert STEP_6_STUDENT in set(DANA_ADVISEE_IDS), \
        f"{STEP_6_STUDENT} must be one of dana's advisees or she cannot ask about him"
    step6_options, step6_blocked, step6_now = next_term_shape(step6)
    assert len(step6_options) == 3, (
        f"{STEP_6_STUDENT} should have three open next-term courses, got {step6_options}"
    )
    assert all(code in NEXT_TERM_OFFERED for code in step6_options), \
        f"{STEP_6_STUDENT}'s open courses must actually be offered next term"
    assert len(step6_blocked) == 1, (
        f"{STEP_6_STUDENT} needs exactly one prereq-blocked course for the beat to "
        f"land, got {step6_blocked}"
    )
    assert step6_now, f"{STEP_6_STUDENT} should be mid-program, not sitting out the term"
    assert step6["last_login_days"] <= 10 and step6["gpa"] >= 3.0, (
        f"{STEP_6_STUDENT} should be an unremarkable student; a struggling one drags "
        "the room back to demo moment 1"
    )

    # S-1042 is NOT the step 6 student and his record is deliberately untouched:
    # he is near the end of his program, so his honest answer is "nothing new to
    # register for until CYB-410 and CYB-420 are finished". Asserted so nobody
    # later "fixes" him into a slide.
    s1042 = state["S-1042"]
    s1042_options, _s1042_blocked, _s1042_now = next_term_shape(s1042)
    assert not s1042_options, (
        "S-1042 is supposed to be the near-complete student with nothing new to "
        f"take; he now has {s1042_options}. Recast demo moment 6, do not retune him."
    )

    # ...and S-1049 must be blocked by an unmet prereq.
    s1049 = state["S-1049"]
    blocked = [code for code, _t, _c, prereqs, _s in CURRICULUM[s1049["program_code"]]
               if code not in s1049["completed"] and not prereqs_met(code, set(s1049["completed"]))]
    assert "BUS-310" in blocked, "S-1049 must be blocked out of BUS-310 by the BUS-150 prereq"

    # Demo moment 5 asks noor about BUS-201-A and needs her refused by name. She
    # must therefore hold no BUS section at all: given one, the model reads her
    # own near-identical id off get_my_sections and answers about that instead,
    # the tool refusal never fires, and the beat loses its point. Asserted so
    # the adjacency cannot come back by accident.
    noor_sections = [sid for sid, _course, sub, _name in SECTIONS if sub == "noor"]
    assert len(noor_sections) == 2, (
        f"SPEC §3 says noor teaches two sections; she has {noor_sections}"
    )
    noor_bus = [sid for sid in noor_sections if sid.startswith("BUS-")]
    assert not noor_bus, (
        f"noor must hold no BUS section, and she holds {noor_bus}. Demo moment 5 "
        "asks her about BUS-201-A and needs the tool refusal to fire; a BUS "
        "section of her own gives the model something adjacent to answer about "
        "instead. Give her a section outside the BUS prefix."
    )

    # Demo moment 7: strong / partial / miss for a CYB-BS graduate.
    #
    # The question the demo actually asks is "which FAST-GROWING occupations
    # would a CYB-BS graduate qualify for", so the trio has to survive that
    # filter. Asserting it across all twelve occupations is what let a 3.1%
    # partial match and an 8.2% miss look correct while being invisible to the
    # question. Everything below is checked inside the fast-growing band.
    cyb = taught["CYB-BS"]
    by_title = {title: set(skills) for _soc, title, _g, _w, skills in OCCUPATIONS}
    fast = {title: set(skills) for _soc, title, growth, _w, skills in OCCUPATIONS
            if growth >= FAST_GROWING_MIN_PCT}

    strong = [t for t, skills in fast.items() if skills <= cyb]
    partial = [t for t, skills in fast.items() if 0 < len(skills & cyb) < len(skills)]
    miss = [t for t, skills in fast.items() if not (skills & cyb)]
    assert strong, f"no fast-growing occupation is a strong CYB-BS match; have {sorted(fast)}"
    assert partial, "no fast-growing occupation is a partial CYB-BS match"
    assert miss, "no fast-growing occupation is a clean CYB-BS miss"

    isa = by_title["Information Security Analysts"]
    assert isa <= cyb, f"CYB-BS must cover every ISA skill; missing {sorted(isa - cyb)}"
    assert "Information Security Analysts" in strong, "ISA must be the fast-growing strong match"
    netadmin = by_title["Network and Computer Systems Administrators"]
    assert "Network and Computer Systems Administrators" in partial, (
        "Network and Computer Systems Administrators is the designated partial match "
        f"and must grow at least {FAST_GROWING_MIN_PCT}% to survive the demo question"
    )
    assert "Data Scientists" in miss, "Data Scientists is the designated fast-growing clean miss"

    # Demo moment 8: the two fast-growers must be unmapped and genuinely gapped.
    mapped = {soc for _p, soc in PROGRAM_OCCUPATION_MAP}
    top3 = sorted(OCCUPATIONS, key=lambda o: -o[2])[:3]
    top3_titles = {o[1] for o in top3}
    assert "Information Security Analysts" in top3_titles
    for title in ("AI/ML Engineers", "Cloud Infrastructure Architects"):
        soc = next(o[0] for o in OCCUPATIONS if o[1] == title)
        assert title in top3_titles, f"{title} must be top-3 by growth"
        assert soc not in mapped, f"{title} must have no program mapped to it"
        overlap = by_title[title] & all_taught
        assert overlap, f"{title} needs credible adjacency to existing outcomes"

    for skill in DELIBERATELY_UNTAUGHT:
        assert skill not in all_taught, f"{skill!r} was supposed to stay untaught"

    ds = by_title["Data Scientists"]
    print("verified:")
    print(f"  dana advises {len(dana_advisees)}, of whom {len(quiet)} have not logged in for >10 days")
    print(f"  demo moment 6 asks about {STEP_6_STUDENT} ({step6['name']}, {step6['program_code']})")
    print(f"    taking now: {', '.join(step6_now)}")
    print(f"    next term:  {', '.join(step6_options)}")
    print(f"    blocked:    {', '.join(step6_blocked)}")
    print(f"  S-1042 keeps his own answer: nothing new next term, {len(_s1042_blocked)} blocked")
    print(f"  S-1049 blocked out of: {', '.join(blocked)}")
    print(f"  noor teaches {', '.join(noor_sections)} and no BUS section")
    print(f"  fast-growing means >= {FAST_GROWING_MIN_PCT}% ({len(fast)} of {len(OCCUPATIONS)} occupations)")
    print(f"  CYB-BS vs Information Security Analysts: {len(isa & cyb)}/{len(isa)} skills (strong)")
    print(f"  CYB-BS vs Network/Systems Administrators: {len(netadmin & cyb)}/{len(netadmin)} (partial)")
    print(f"  CYB-BS vs Data Scientists: {len(ds & cyb)}/{len(ds)} (miss)")
    print(f"  unmapped fast-growers: {', '.join(sorted(top3_titles - {'Information Security Analysts'}))}")
    print(f"  skills no program teaches: {', '.join(sorted(set(DELIBERATELY_UNTAUGHT)))}")


def main() -> None:
    students = make_students()
    state = seed_colleague(students)
    seed_canvas(state)
    seed_kuali()
    seed_labor()
    verify(state)
    print(f"\nwrote {DATA_DIR}/{{colleague,canvas,kuali,labor}}.db")


if __name__ == "__main__":
    main()
