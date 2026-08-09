"""What the tools put in front of the model, beyond who may call them.

test_auth.py pins the boundaries: who is refused, and in what words. These
tests pin the *content* of a successful result, for the few fields whose whole
purpose is to stop the model inventing something. They are not auth tests and
they do not belong in that file.

Each field here exists because a demo answer went wrong without it:

  * `open_because` on a next-term option — a blocked option always stated its
    blocker, so an open one was the only thing in the result with no stated
    reason, and the model read that silence as "the prerequisite is not
    completed" about a prerequisite completed two terms ago.
  * the count fields — `advisee_count`, `student_count`, `program_count` — one
    per tool whose result the model kept miscounting on stage: "your 24
    advisees" about 25 people, "none of the six programs" two sentences after a
    tally of four. Each count is computed from the very list it ships with, so
    the number and the list cannot disagree.
  * `flagged_count` and `quiet_count` on the advisee roster — the same fault one
    level in. Once the total came from the tool, the subsets went wrong in its
    place: "eight of your advisees have flags" above a list of nine.

They run against the live stack with real tokens, like everything else here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import pytest

from conftest import MCP_SERVERS, mcp_session

# The student demo moment 6 asks about (DEMO_VERIFICATION.md's casting table,
# and STEP_6_STUDENT in scripts/seed.py). Mid-programme on purpose: three open
# options and one blocked by a prerequisite he has not taken.
STEP_6_STUDENT = "S-1055"

# A term as scripts/seed.py writes it: 2025SP, 2024FA. Matched by shape rather
# than by value so a re-seed that moves the terms along does not fail a test
# about whether the term is stated at all.
TERM = re.compile(r"\b20\d{2}(SP|SU|FA)\b")
GRADE = re.compile(r"\(([A-D][+-]?)\)")

# What "quiet" means, matching QUIET_AFTER_DAYS in services/mcp-colleague/app.py.
# Written out rather than imported: this workspace does not install the server's
# dependencies, and every other test here reaches the servers over MCP too.
QUIET_AFTER_DAYS = 10


def structured(text: str) -> dict[str, Any]:
    """The tool's structured result, out of the text blocks conftest joins.

    `MCPSession.call_tool` appends `structuredContent` as its last chunk, so
    the last JSON object in the text is the typed payload.
    """
    for line in reversed(text.splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError(f"no structured content in tool result: {text[:300]}")


@pytest.mark.session2
def test_every_open_next_term_option_says_why_it_is_open(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """SPEC §4.4: the open options carry their licence, not just their names.

    A blocked option states its blocker. Until an open one stated the
    prerequisites it satisfied — with the term completed and the grade — the
    only way to learn why a course was offered was to call a second tool, and
    demo moment 6 instead asserted a false fact about S-1055's CS-320.
    """
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("dana")) as session:
        result = session.call_tool("get_next_term_options", {"student_id": STEP_6_STUDENT})
    assert not result.refused, (
        f"{STEP_6_STUDENT} is one of dana's advisees and must be served: {result.text[:300]}"
    )

    options = structured(result.text)["options"]
    assert options, (
        f"{STEP_6_STUDENT} should have open next-term options; scripts/seed.py::verify "
        "asserts three. Got none."
    )

    for option in options:
        reason = option.get("open_because")
        assert reason, f"{option['course_code']} states no reason it is open: {option}"
        assert reason.startswith("open:"), (
            f"{option['course_code']}'s reason should open with 'open:', got {reason!r}"
        )
        if not option["prereqs"]:
            assert reason == "open: no prerequisites", (
                f"{option['course_code']} has no prereqs, so its reason should say so, "
                f"got {reason!r}"
            )
            continue
        for prereq in option["prereqs"]:
            assert prereq in reason, (
                f"{option['course_code']}'s reason must name the satisfied prerequisite "
                f"{prereq}, got {reason!r}"
            )
        assert TERM.search(reason), (
            f"{option['course_code']}'s reason must state when the prerequisite was "
            f"completed, got {reason!r}"
        )
        assert GRADE.search(reason), (
            f"{option['course_code']}'s reason must state the grade earned, got {reason!r}"
        )

    # The specific fact demo moment 6 got wrong. CS-410 is open only because
    # CS-320 is done, and this is the sentence that says so.
    by_code = {option["course_code"]: option["open_because"] for option in options}
    assert "CS-410" in by_code, (
        f"{STEP_6_STUDENT}'s open options should include CS-410, got {sorted(by_code)}"
    )
    assert "CS-320 completed" in by_code["CS-410"], (
        "CS-410 is open because CS-320 is completed, and the result must say so. "
        f"Got {by_code['CS-410']!r}"
    )


# --------------------------------------------------------------------------
# The count fields. One test per enriched tool, each asserting the same thing:
# the count is present, and it equals the length of the list it describes. A
# count that could drift from its own list would be worse than no count at all
# — the model is being told to trust it verbatim.
# --------------------------------------------------------------------------


@pytest.mark.session2
def test_the_advisee_roster_states_how_many_advisees_it_holds(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("dana")) as session:
        result = session.call_tool("get_my_advisees", {})
    assert not result.refused, f"dana holds the advisor role and must be served: {result.text[:300]}"

    payload = structured(result.text)
    assert "advisee_count" in payload, (
        f"get_my_advisees must state its own total: {sorted(payload)}"
    )
    assert payload["advisee_count"] == len(payload["advisees"]), (
        f"advisee_count {payload['advisee_count']} disagrees with the "
        f"{len(payload['advisees'])} advisees beside it"
    )
    assert payload["advisee_count"] > 0, "dana's roster came back empty; check scripts/seed.py"


def dana_roster(token: str) -> dict[str, Any]:
    with mcp_session(MCP_SERVERS["mcp-colleague"], token) as session:
        result = session.call_tool("get_my_advisees", {})
    assert not result.refused, f"dana holds the advisor role and must be served: {result.text[:300]}"
    return structured(result.text)


@pytest.mark.session2
def test_the_advisee_roster_counts_its_own_flagged_students(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """The tally demo moment 1 opens with, counted by the tool.

    advisee_count closed the total; the subset then went wrong in its place —
    "eight of your advisees have flags" written above a list of nine, three runs
    out of three.
    """
    payload = dana_roster(token_for("dana"))
    assert "flagged_count" in payload, (
        f"get_my_advisees must state flagged_count: {sorted(payload)}"
    )
    flagged = [a for a in payload["advisees"] if a["term_grade_flags"]]
    assert payload["flagged_count"] == len(flagged), (
        f"flagged_count {payload['flagged_count']} disagrees with the {len(flagged)} "
        "advisees carrying a term grade flag"
    )
    # Zero would satisfy the equality above while telling the demo nothing.
    # scripts/seed.py::verify pins this at 9.
    assert payload["flagged_count"] > 0, (
        "demo moment 1 opens with this tally and no advisee is flagged; check "
        "scripts/seed.py"
    )


@pytest.mark.session2
def test_the_advisee_roster_counts_its_own_quiet_students(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """The other half of demo moment 1's opening sentence.

    "Quiet" is more than QUIET_AFTER_DAYS days since the last login, the same
    threshold the dean's per-program percentage uses.
    """
    payload = dana_roster(token_for("dana"))
    assert "quiet_count" in payload, (
        f"get_my_advisees must state quiet_count: {sorted(payload)}"
    )
    quiet = [a for a in payload["advisees"] if a["last_login_days"] > QUIET_AFTER_DAYS]
    assert payload["quiet_count"] == len(quiet), (
        f"quiet_count {payload['quiet_count']} disagrees with the {len(quiet)} advisees "
        f"who have not logged in for more than {QUIET_AFTER_DAYS} days"
    )
    # scripts/seed.py::verify pins this at 8.
    assert payload["quiet_count"] > 0, (
        "demo moment 1 depends on a visible quiet tail and there is none; check "
        "scripts/seed.py"
    )


@pytest.mark.session2
def test_section_engagement_states_how_many_students_it_holds(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    """noor's own section, so this is a served call rather than a refusal."""
    with mcp_session(MCP_SERVERS["mcp-canvas"], token_for("noor")) as session:
        result = session.call_tool("get_section_engagement", {"section_id": "CYB-310-A"})
    assert not result.refused, f"CYB-310-A is noor's own section: {result.text[:300]}"

    payload = structured(result.text)
    assert "student_count" in payload, (
        f"get_section_engagement must state its own total: {sorted(payload)}"
    )
    assert payload["student_count"] == len(payload["students"]), (
        f"student_count {payload['student_count']} disagrees with the "
        f"{len(payload['students'])} student rows beside it"
    )
    assert payload["student_count"] == payload["enrollment"], (
        "student_count and enrollment count the same activity rows and must agree: "
        f"{payload['student_count']} vs {payload['enrollment']}"
    )


@pytest.mark.session2
def test_program_summaries_states_how_many_programs_it_holds(
    session2_stack: None, token_for: Callable[[str], str]
) -> None:
    with mcp_session(MCP_SERVERS["mcp-colleague"], token_for("kim")) as session:
        result = session.call_tool("get_program_summaries", {})
    assert not result.refused, f"kim holds the dean role and must be served: {result.text[:300]}"

    payload = structured(result.text)
    assert "program_count" in payload, (
        f"get_program_summaries must state its own total: {sorted(payload)}"
    )
    assert payload["program_count"] == len(payload["programs"]), (
        f"program_count {payload['program_count']} disagrees with the "
        f"{len(payload['programs'])} programs beside it"
    )
    assert payload["program_count"] > 0, "the catalog came back empty; check scripts/seed.py"
