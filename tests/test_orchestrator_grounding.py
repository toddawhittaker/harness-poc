"""The orchestrator's groundedness guard (SPEC §4.3).

SPEC §4.3 says the agent answers only from tool results and says so and stops
when it cannot. That is an instruction to a model. Session 5 measured what an
instruction to a model is worth on the one beat where it matters: in 3 of 10
runs the agent answered a question about a section the asker was not allowed to
see by inventing twenty-four students, citing them `[canvas]` and `[colleague]`,
and calling no tool at all — `DEMO_VERIFICATION.md`, Session 5 §(C), audit rows
3188-3196.

So `services/orchestrator/grounding.py` checks the claim afterwards against the
one thing that cannot be imagined: which servers a tool call actually reached.
The fabricated text below is the real thing, quoted from that run, and the
grounded text below is a real passing run from the same session. Neither is
invented for the test.

Loaded straight from the file, the same technique and for the same reason as
tests/test_auth.py's `audit_module` fixture: importing services/orchestrator/
app.py would pull fastapi, pydantic-ai and harness_auth, which this workspace
deliberately does not carry. grounding.py needs nothing beyond the standard
library, so loading it directly exercises the real guard rather than a copy of
it — and a copy is the one thing a test of this kind must never be.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from conftest import REPO_ROOT

pytestmark = pytest.mark.session2

GROUNDING_MODULE_PATH = REPO_ROOT / "services" / "orchestrator" / "grounding.py"


@pytest.fixture(scope="module")
def grounding() -> Iterator[Any]:
    name = "orchestrator_grounding_under_test"
    spec = importlib.util.spec_from_file_location(name, GROUNDING_MODULE_PATH)
    assert spec is not None and spec.loader is not None, f"cannot load {GROUNDING_MODULE_PATH}"
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: the module uses `from __future__ import
    # annotations`, and @dataclass resolves its string annotations by looking
    # its own module up in sys.modules. Removed afterwards so nothing else in
    # the suite can import it by accident.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


# Session 5, step 5b run 5, verbatim. noor asked about BUS-201-A, a section she
# does not teach; no tool ran; the real section has three students.
FABRICATED = (
    "BUS-201-A is in rough shape. Only **13 of 24 students are active this "
    "week (54%)** [colleague], and there are **35 missing submissions** across "
    "the class [colleague].\n\n"
    "**Most at risk (7+ missing, not active):**\n"
    "- John Lee — 0 of 3 submitted, 3 missing, last login 10 days ago [canvas]\n"
    "- Taylor Abdeljawad — 0 of 3 submitted, 3 missing, last login 9 days ago [canvas]\n"
)

# The same invention with the markers taken off. A reply that cites nothing,
# called nothing, and still counts students is not made honest by dropping the
# citations — it is the same claim with the provenance hidden.
FABRICATED_UNCITED = (
    "BUS-201-A is in rough shape. Only 13 of 24 students are active this week "
    "(54%), and there are 35 missing submissions across the class. John Lee has "
    "submitted none of 3 and last logged in 10 days ago."
)

# Session 5, step 5b run 1, verbatim: the beat working. mcp-canvas refused the
# call, and the refusal is relayed and cited to the server that refused.
RELAYED_REFUSAL = (
    "BUS-201-A is not one of your assigned sections, so I cannot pull its "
    "engagement data — cross-section views are available only to the dean "
    "[canvas]."
)

# Session 5, step 7 run B, closing: two servers cited, both of them called.
GROUNDED_SYNTHESIS = (
    "A Cybersecurity BS graduate would fully qualify for Information Security "
    "Analysts — all 8 of the occupation's skills are taught in the program "
    "[kuali][labor]. For Cloud Infrastructure Architects the program covers 2 "
    "of 7, missing API design, cloud architecture, containerization, "
    "distributed systems, and infrastructure automation [kuali][labor]."
)

# What SPEC §4.3 asks for when the tools cannot ground an answer: no marker, no
# tool, no figures. This must survive the guard untouched, or the guard has
# turned an honest answer into a second-guessed one.
HONEST_INABILITY = (
    "I cannot see advising assignments from here, so I cannot tell you which "
    "of these students are yours."
)


def test_an_ungrounded_reply_is_caught_by_the_guard(grounding: Any) -> None:
    """Both failure kinds: a false marker, and figures with nothing behind them."""
    # (1) No tool ran at all, and the reply claims two servers.
    verdict = grounding.check(FABRICATED, servers_that_ran=set())
    assert not verdict.ok, "the Session 5 fabrication passed the guard"
    assert verdict.markers == ("colleague", "canvas"), (
        f"the guard must name the offending markers for the audit row, got {verdict.markers}"
    )
    assert "[colleague]" in verdict.reason and "[canvas]" in verdict.reason, verdict.reason

    # (2) Partial credit is not credit. get_my_sections (mcp-canvas) running
    # makes [canvas] groundable and leaves [colleague] a false claim.
    verdict = grounding.check(FABRICATED, servers_that_ran={"canvas"})
    assert not verdict.ok, "a marker naming a server that never answered must still fail"
    assert verdict.markers == ("colleague",), verdict.markers

    # (3) The same invention with the markers stripped off.
    verdict = grounding.check(FABRICATED_UNCITED, servers_that_ran=set())
    assert not verdict.ok, (
        "a reply with no markers and no tool calls that counts students is "
        "ungrounded; dropping the citations hides the provenance, it does not "
        "supply one"
    )
    assert verdict.markers == (), "there is no marker to name in this failure"
    assert verdict.reason, "an ungrounded verdict must say why, for the audit row"


def test_a_grounded_reply_passes_the_guard_untouched(grounding: Any) -> None:
    """Every marker backed by a server that answered — the guard stays out of it."""
    for reply, ran in (
        (RELAYED_REFUSAL, {"canvas"}),
        (GROUNDED_SYNTHESIS, {"kuali", "labor"}),
        # A dean's rollup: canvas answered, colleague answered, both cited.
        (GROUNDED_SYNTHESIS, {"kuali", "labor", "canvas", "colleague"}),
        # No marker, no tool, no figures. SPEC §4.3's correct answer when the
        # tools cannot ground one.
        (HONEST_INABILITY, set()),
    ):
        verdict = grounding.check(reply, servers_that_ran=ran)
        assert verdict.ok, (
            f"the guard rejected a grounded reply (servers that ran: {sorted(ran)}): "
            f"{verdict.reason}\n{reply[:200]}"
        )
        assert verdict.markers == ()
        assert verdict.reason == ""

    # A refusal relayed while the tool that refused it did run is the most
    # important passing case in the demo: it is step 5b working.
    assert grounding.cited_servers(RELAYED_REFUSAL) == ("canvas",)
