"""What `tools_used` means on the receipt (SPEC §4.3, §7 step 4).

A model can emit a call for a tool that was never in its schema. Nothing runs:
registry filtering kept the tool out of the model's view, so no MCP client was
built for it and no server was dialled. But the call is still a part in the
run's messages, and until `executed_and_unoffered` split them apart it flowed
straight into `tools_used`, into a green `answer_returned` row, and into the
bypass script's own summary — `DEMO_VERIFICATION.md`, Session 8 §7.1, audit rows
4652-4653, where pat's receipt named `get_my_sections` two lines above the
narration that pat's non-labor tools "were never placed in the model's view".

So: `tools_used` means EXECUTED, `unoffered_calls` names the attempts, and
`tools_used ⊆ tools_offered` holds on every audit row.

The functions are read out of `services/orchestrator/app.py` rather than
imported, for the same reason `test_orchestrator_grounding.py` loads
`grounding.py` directly: importing that module would pull fastapi, pydantic-ai
and harness_auth, which this workspace deliberately does not carry. Here the
whole module cannot be executed at all, so the two function definitions are
lifted from the parsed source and compiled on their own. That still exercises
the shipped code — an edit to app.py changes what runs here — and a transcribed
copy is the one thing a test of this kind must never be.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

import pytest

from conftest import REPO_ROOT

pytestmark = pytest.mark.session2

ORCHESTRATOR_APP = REPO_ROOT / "services" / "orchestrator" / "app.py"

# pat's allowlist from config/registry.yaml: public labor data and nothing else.
PAT_TOOLS = {"list_occupations", "get_occupation"}


@dataclass
class StubToolCallPart:
    """Stands in for pydantic_ai.ToolCallPart, which this workspace has no copy of.

    `tools_called` tests parts with `isinstance(part, ToolCallPart)`, and the
    lifted function is compiled against whatever `ToolCallPart` is in the
    namespace it is given — so a stub here is the real branch, not a bypass of
    it. Only the one attribute the function reads is modelled.
    """

    tool_name: str


@dataclass
class StubTextPart:
    """A part that is not a tool call, so the isinstance branch has something to reject."""

    content: str


@dataclass
class StubMessage:
    parts: list[Any]


@dataclass
class StubRun:
    """The shape `tools_called` consumes: a run that can list its own messages."""

    messages: list[StubMessage]

    def all_messages(self) -> list[StubMessage]:
        return self.messages


def orchestrator_functions() -> dict[str, Any]:
    """`tools_called` and `executed_and_unoffered`, lifted from the shipped file."""
    tree = ast.parse(ORCHESTRATOR_APP.read_text(), filename=str(ORCHESTRATOR_APP))
    wanted = ("tools_called", "executed_and_unoffered")
    found = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in wanted]
    missing = set(wanted) - {node.name for node in found}
    assert not missing, (
        f"{ORCHESTRATOR_APP} no longer defines {sorted(missing)} at module level; "
        "the receipt semantics moved and this test is looking at the wrong place"
    )
    namespace: dict[str, Any] = {"ToolCallPart": StubToolCallPart, "Any": Any}
    exec(compile(ast.Module(body=found, type_ignores=[]), str(ORCHESTRATOR_APP), "exec"),
         namespace)
    return namespace


def phantom_run() -> StubRun:
    """Session 8 §7.1, in miniature: two real labor calls and one pat never held."""
    return StubRun([
        StubMessage([StubTextPart("Asked by Pat Reyes (roles: adjunct).")]),
        StubMessage([StubToolCallPart("list_occupations")]),
        StubMessage([StubToolCallPart("get_my_sections")]),        # the phantom
        StubMessage([StubToolCallPart("get_occupation"),
                     StubTextPart("Information Security Analysts grow 32.7% [labor].")]),
        # Called twice in one run; the receipt names a tool once.
        StubMessage([StubToolCallPart("list_occupations")]),
    ])


def test_a_phantom_tool_call_is_not_reported_as_a_tool_that_ran() -> None:
    """The bypass beat's receipt: pat's row may not claim a canvas tool ran."""
    functions = orchestrator_functions()
    called = functions["tools_called"](phantom_run())
    assert called == ["list_occupations", "get_my_sections", "get_occupation"], (
        f"tools_called must report every call in order, deduplicated; got {called}"
    )

    used, unoffered = functions["executed_and_unoffered"](called, PAT_TOOLS)
    assert "get_my_sections" not in used, (
        "a tool outside the offered set reached no server and must not appear in "
        f"tools_used; got {used}"
    )
    assert used == ["list_occupations", "get_occupation"], used
    assert set(used) <= PAT_TOOLS, "tools_used must be a subset of tools_offered"
    assert unoffered == ["get_my_sections"], (
        "the attempt is not swallowed — unoffered_calls has to name it, or the "
        f"receipt hides a model reaching for a tool it does not hold; got {unoffered}"
    )


def test_an_ordinary_run_reports_no_unoffered_calls() -> None:
    """Empty on every normal request, which is what makes a non-empty one worth seeing."""
    functions = orchestrator_functions()
    run = StubRun([
        StubMessage([StubToolCallPart("get_occupation")]),
        StubMessage([StubTextPart("Median wage 120360 [labor].")]),
    ])
    used, unoffered = functions["executed_and_unoffered"](
        functions["tools_called"](run), PAT_TOOLS)
    assert used == ["get_occupation"]
    assert unoffered == [], f"a run inside the allowlist must report nothing attempted: {unoffered}"

    # And a reply that called nothing at all — the shape the grounding guard
    # catches — leaves both lists empty rather than one of them unset.
    used, unoffered = functions["executed_and_unoffered"](
        functions["tools_called"](StubRun([StubMessage([StubTextPart("no tools here")])])),
        PAT_TOOLS)
    assert used == [] and unoffered == []
