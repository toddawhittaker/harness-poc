"""Is a reply grounded in the tools that actually ran? (SPEC §4.3)

SPEC §4.3 tells the agent to answer only from tool results and to say so and
stop when it cannot. That is an instruction to a model, and a model is not an
enforcement boundary — the same principle the rest of this system is built on.
Session 5 measured the gap: in 3 of 10 runs the model answered a question about
a section it was not allowed to see by inventing twenty-four students, citing
them `[canvas]` and `[colleague]`, and calling no tool at all. Nothing in the
audit trail contradicted it, because nothing in the audit trail existed.

So the claim is checked after the fact, mechanically, against the one thing that
cannot be imagined: which servers a tool call actually reached this request.

Two ways a reply fails:

1. It carries a citation marker naming a server no tool call reached. The marker
   is a claim of provenance and the provenance is checkable.
2. It cites nothing, called nothing, and still states figures about students or
   sections. A number about people is a claim about the record; with no tool
   behind it there is nothing it can be a claim from.

Deliberately NOT checked here: whether the marker on a given sentence is the
*right* one of the servers that ran. That is a citation-accuracy problem, it is
the system prompt's job, and a guard that guessed at it would start rewriting
correct answers.

No imports beyond the standard library, on purpose: tests/test_auth.py loads
this file directly (the test workspace carries neither fastapi nor pydantic-ai),
so the guard under test is this code and not a copy of it.
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass

# The four citation markers ground rule 2 defines. Same four names as
# app.py's MCP_SERVERS, and that is the whole idea: the marker IS the server,
# so a marker can be checked against the servers that answered.
MARKERS: frozenset[str] = frozenset({"colleague", "canvas", "kuali", "labor"})

_MARKER = re.compile(r"\[([A-Za-z-]+)\]")

# A digit alone means nothing — "$120,360" is a wage and wages come from labor.
# A digit next to any of these words is a claim about people or rooms, which is
# the thing that must never be composed. Kept as one flat list rather than
# anything cleverer: it is read on a projector and edited by hand.
_ABOUT_PEOPLE = re.compile(
    r"\b(student|students|section|sections|advisee|advisees|roster|rosters|"
    r"enrolled|enrollment|gpa|submitted|submission|submissions|missing|"
    r"logged in|last login|logins|inactive|attendance)\b",
    re.IGNORECASE,
)
_A_NUMBER = re.compile(r"\d")


@dataclass(frozen=True)
class Verdict:
    """`ok` false means the reply must not be returned as it stands.

    `markers` names the offending citations — empty when the failure is the
    second kind, which has no marker to name. `reason` is written to be read
    twice: once by the model, in the corrective message, and once by whoever is
    looking at the audit row afterwards.
    """

    ok: bool
    markers: tuple[str, ...] = ()
    reason: str = ""


def cited_servers(reply: str) -> tuple[str, ...]:
    """Distinct citation markers in the reply, in the order they first appear."""
    found: list[str] = []
    for match in _MARKER.finditer(reply):
        name = match.group(1).lower()
        if name in MARKERS and name not in found:
            found.append(name)
    return tuple(found)


def states_figures_about_people(reply: str) -> bool:
    """A number and a word that makes the number about students or sections.

    Coarse on purpose, and it errs towards flagging. The cost of a false
    positive is one regeneration of a reply that had no tool call behind it
    anyway; the cost of a false negative is an invented roster on the slide
    whose point is that the boundary holds.
    """
    return bool(_A_NUMBER.search(reply)) and bool(_ABOUT_PEOPLE.search(reply))


def check(reply: str, servers_that_ran: Collection[str]) -> Verdict:
    """Judge one reply against the servers a tool call actually reached."""
    ran = set(servers_that_ran)
    cited = cited_servers(reply)
    ungrounded = tuple(name for name in cited if name not in ran)

    if ungrounded:
        markers = ", ".join(f"[{name}]" for name in ungrounded)
        served = ", ".join(sorted(ran)) if ran else "no server"
        return Verdict(
            ok=False,
            markers=ungrounded,
            reason=f"cited {markers}, but this request reached {served}.",
        )

    if not ran and not cited and states_figures_about_people(reply):
        return Verdict(
            ok=False,
            reason="states figures about students or sections with no tool call behind them.",
        )

    return Verdict(ok=True)
