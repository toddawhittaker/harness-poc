"""Per-intent reasoning routing (Session 16).

`AGENT_THINKING` was one switch for the whole build, and Session 11 measured why
that is the wrong shape: extended reasoning removes the arithmetic defect class
and costs demo moment 5 its tool-layer refusal about half the time. One switch
forces one answer to a question that has two. So the router now assigns a
reasoning budget per question, from a table in the gateway, and the orchestrator
spends what it is given.

Three things have to hold, and this file pins each of them:

  * `agent_model(reasoning=...)` must set the budget for ONE call and leave the
    env default alone — a per-request override that quietly rewrote a module
    constant would make every later request depend on the last one.
  * The table must assign what it says it assigns, for every beat in the demo
    script, including the fail-open path and a caller holding two roles.
  * The receipt must state which budget answered, or the measurement of any
    beat that behaves differently is guesswork afterwards.

`factory.py` and `app.py` are read out of the shipped files rather than
imported, the same technique and for the same reason as
`test_orchestrator_receipts.py`: this workspace deliberately carries no
pydantic, pydantic-ai or fastapi. The definitions are lifted from the parsed
source and compiled against stubs, so an edit to either file changes what runs
here — and a transcribed copy is the one thing a test of this kind must never
be.
"""

from __future__ import annotations

import ast
import inspect
import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import httpx
import pytest

from conftest import (
    CHAT_TIMEOUT_SECONDS,
    ORCHESTRATOR_URL,
    REPO_ROOT,
    fetch_events,
    utcnow,
    wait_for_event,
)

pytestmark = pytest.mark.session2

FACTORY = REPO_ROOT / "libs" / "harness_models" / "src" / "harness_models" / "factory.py"
GATEWAY_APP = REPO_ROOT / "services" / "gateway" / "app.py"

ENABLED = {"thinking": {"type": "enabled"}}
DISABLED = {"thinking": {"type": "disabled"}}


# --------------------------------------------------------------------------
# Stubs for the three provider classes the factory builds. Each models only
# the attributes the lifted code sets, so what runs is the real branch.
# --------------------------------------------------------------------------


@dataclass
class StubModelSettings:
    extra_body: dict[str, Any] = field(default_factory=dict)


@dataclass
class StubProvider:
    base_url: str
    api_key: str


@dataclass
class StubModel:
    name: str
    provider: Any = None
    settings: Any = None


def lifted(path: Any, wanted: tuple[str, ...], namespace: dict[str, Any]) -> dict[str, Any]:
    """Named module-level definitions from a shipped file, in source order.

    Source order matters: `AGENT_SETTINGS = _settings(AGENT_THINKING)` runs at
    module level and has to see the function above it, exactly as it does in the
    real import.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    body: list[ast.stmt] = []
    seen: set[str] = set()
    for node in tree.body:
        name = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            name = node.targets[0].id
        if name in wanted:
            body.append(node)
            seen.add(name)

    missing = set(wanted) - seen
    assert not missing, (
        f"{path} no longer defines {sorted(missing)} at module level; the reasoning "
        "routing moved and this test is looking at the wrong place"
    )
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def factory() -> dict[str, Any]:
    """The model factory, compiled against stub provider classes."""
    return lifted(
        FACTORY,
        ("BASE_URL", "API_KEY", "ROUTER_MODEL", "AGENT_MODEL", "_thinking",
         "AGENT_THINKING", "ROUTER_THINKING", "_settings", "AGENT_SETTINGS",
         "ROUTER_SETTINGS", "_model", "router_model", "agent_model"),
        {"os": os, "ModelSettings": StubModelSettings, "OpenAIChatModel": StubModel,
         "OpenAIProvider": StubProvider},
    )


def gateway() -> dict[str, Any]:
    """The reasoning table and the function that reads it."""
    return lifted(
        GATEWAY_APP,
        ("REASONING_BY_CATEGORY", "REASONING_DEFAULT", "reasoning_for"),
        {},
    )


# --------------------------------------------------------------------------
# The factory — a per-request budget that stays per-request.
# --------------------------------------------------------------------------


def test_the_reasoning_override_sets_the_thinking_body_for_one_call() -> None:
    """True and False are this request's budget; the env default is untouched."""
    models = factory()
    default = models["AGENT_SETTINGS"].extra_body

    assert models["agent_model"](True).settings.extra_body == ENABLED, (
        "agent_model(True) must send DeepSeek's thinking object enabled"
    )
    assert models["agent_model"](False).settings.extra_body == DISABLED, (
        "agent_model(False) must send it disabled — an override that only ever "
        "turns reasoning ON cannot protect a beat that needs it off"
    )
    assert models["AGENT_SETTINGS"].extra_body == default, (
        "the module-level settings object was mutated by a per-request override; "
        "every later request would then depend on the last one"
    )


def test_no_argument_means_the_environment_default() -> None:
    """None is not False. AGENT_THINKING still decides when nobody says otherwise."""
    models = factory()
    expected = ENABLED if models["AGENT_THINKING"] else DISABLED

    assert models["agent_model"]().settings.extra_body == expected
    assert models["agent_model"](None).settings.extra_body == expected
    assert (
        inspect.signature(models["agent_model"]).parameters["reasoning"].default is None
    ), "the default must be None — 'the env default' and 'no reasoning' are different answers"


def test_the_router_model_takes_no_reasoning_argument() -> None:
    """SPEC §4.2's triage step is a half-second job; there is no budget to assign it."""
    models = factory()
    assert not inspect.signature(models["router_model"]).parameters, (
        "router_model() gained a parameter; the router's own mode is ROUTER_THINKING "
        "and nothing per-request should reach it"
    )
    assert models["router_model"]().settings is models["ROUTER_SETTINGS"]


# --------------------------------------------------------------------------
# The table — every beat in the demo script, by the intent the router really
# assigns it (DEMO_VERIFICATION.md, Session 15 rows 8552-8660).
# --------------------------------------------------------------------------


# (beat, router intent, roles, budget)
BEATS: list[tuple[str, str, list[str], bool]] = [
    ("1  dana, struggling students", "advisee_detail", ["advisor"], False),
    ("2  kim, struggling students", "advisee_detail", ["dean"], True),
    ("2b kim, same with plain language", "advisee_detail", ["dean"], True),
    ("3a pat, struggling students", "advisee_detail", ["adjunct"], False),
    ("3b pat, fastest-growing occupations", "labor_market", ["adjunct"], False),
    ("5a noor, her own section", "program_aggregate", ["faculty"], False),
    ("5b noor, a section she does not teach", "program_aggregate", ["faculty"], False),
    ("5c kim, the rollup", "program_aggregate", ["dean"], True),
    ("6  dana, next term for S-1055", "advisee_detail", ["advisor"], False),
    ("7  kim, qualification synthesis", "labor_market", ["dean"], True),
    ("8  kim, gap synthesis", "labor_market", ["dean"], True),
]


@pytest.mark.parametrize("beat,intent,roles,expected", BEATS,
                         ids=[beat.split()[0] + "-" + roles[0] for beat, _, roles, _ in BEATS])
def test_every_demo_beat_gets_the_budget_the_table_assigns(
    beat: str, intent: str, roles: list[str], expected: bool
) -> None:
    """The table is the specification of which beats cost reasoning."""
    assert gateway()["reasoning_for"](intent, roles) is expected, (
        f"beat {beat} classified {intent} for roles {roles} must be "
        f"reasoning={expected}"
    )


def test_the_protected_beat_is_cheap_and_says_so_in_the_table() -> None:
    """Moment 5 is the load-bearing cell. Session 11 measured what reasoning costs it."""
    table = gateway()["REASONING_BY_CATEGORY"]
    assert table[("program_aggregate", "faculty")] is False, (
        "a faculty caller's section question must not be routed to reasoning: the "
        "tool-layer refusal demo moment 5 turns on stopped reaching the server in "
        "about half of ten runs under it (docs/LESSONS.md entry 9)"
    )


def test_the_fail_open_path_is_also_fail_cheap() -> None:
    """A router that could not speak buys nothing. `unclassified` is not in the table."""
    reasoning_for = gateway()["reasoning_for"]
    assert reasoning_for("unclassified", ["dean"]) is False
    assert reasoning_for("other", ["dean"]) is False
    assert reasoning_for("something the model improvised", ["dean"]) is False
    assert reasoning_for("labor_market", []) is False, (
        "a caller with no roles matches no cell and takes the default"
    )


def test_a_caller_holding_two_roles_gets_the_budget_if_either_role_asks_for_it() -> None:
    """sam is advisor and dean. Generosity with a budget is harmless; ambiguity is not."""
    reasoning_for = gateway()["reasoning_for"]
    assert reasoning_for("advisee_detail", ["advisor", "dean"]) is True
    assert reasoning_for("advisee_detail", ["dean", "advisor"]) is True, (
        "the answer must not depend on the order the roles arrive in"
    )


def test_the_table_defaults_to_no_reasoning() -> None:
    assert gateway()["REASONING_DEFAULT"] is False


# --------------------------------------------------------------------------
# End to end — the budget on the wire, and on the receipt.
# --------------------------------------------------------------------------


# One tool call and a short answer, so the live half of this file costs the
# suite one cheap request per budget rather than a demo beat.
PROBE = "What is the median wage for information security analysts?"

# sam, the persona SPEC §3 keeps in reserve, and the reason to use her here is
# isolation rather than her roles: no other test in the suite drives a chat as
# sam, so the rows these three tests write cannot be picked up by another test
# polling for the persona it just asked about. tests/test_skills.py does exactly
# that for pat, two seconds either side.
PROBE_PERSONA = "sam"


def newest_row_id(client: httpx.Client) -> int:
    """The audit watermark before a request, so the row after it is identifiable.

    Timestamps are written to whole seconds, which is coarse enough that a
    `since` filter alone can match the previous test's row instead of this
    one's. The row id cannot tie.
    """
    rows = fetch_events(client, limit=1)
    return int(rows[0]["id"]) if rows else 0


def answer_row(client: httpx.Client, sub: str, after_id: int) -> dict[str, Any]:
    """The `answer_returned` row this request wrote, and no earlier one."""
    row = wait_for_event(
        client,
        lambda event: (event.get("event") == "answer_returned"
                       and event.get("sub") == sub
                       and int(event.get("id", 0)) > after_id),
        # The id test is what identifies the row; the timestamp filter only has
        # to be loose enough not to exclude it.
        since=utcnow() - timedelta(minutes=10),
        timeout=20.0,
    )
    assert row is not None, f"no answer_returned row for {sub} after row {after_id}"
    return row


def ask(client: httpx.Client, token: str, body: dict[str, Any]) -> httpx.Response:
    """Straight at the orchestrator, so the flag under test is the one set here.

    Through the gateway the router would choose it, and a test of the plumbing
    would become a test of a model's classification.
    """
    response = client.post(
        f"{ORCHESTRATOR_URL}/chat",
        json={"message": PROBE, "history": [], **body},
        headers={"Authorization": f"Bearer {token}"},
        timeout=CHAT_TIMEOUT_SECONDS,
    )
    assert response.status_code == 200, response.text[:300]
    return response


@pytest.mark.parametrize("requested", [True, False], ids=["reasoning", "cheap"])
def test_a_requests_budget_reaches_the_model_and_lands_on_the_receipt(
    session2_stack: None, http: httpx.Client, token_for: Any, requested: bool
) -> None:
    """The orchestrator spends what it is handed, and the row says what it spent."""
    watermark = newest_row_id(http)
    ask(http, token_for(PROBE_PERSONA), {"reasoning": requested})

    detail = answer_row(http, PROBE_PERSONA, watermark).get("detail") or {}
    assert detail.get("reasoning") is requested, (
        "answer_returned must state which budget answered; got "
        f"{detail.get('reasoning')!r} for a request that asked for {requested}"
    )


def test_a_caller_that_sends_no_budget_inherits_the_environment_default(
    session2_stack: None, http: httpx.Client, token_for: Any
) -> None:
    """scripts/demo_bypass.sh skips the gateway and sends no flag.

    The bypass beat therefore runs on AGENT_THINKING, unchanged by this routing —
    which is the property that keeps demo moment 4 deterministic.
    """
    watermark = newest_row_id(http)
    ask(http, token_for(PROBE_PERSONA), {})

    detail = answer_row(http, PROBE_PERSONA, watermark).get("detail") or {}
    assert detail.get("reasoning") is factory()["AGENT_THINKING"], (
        "a request with no reasoning field must take the env default, not False by "
        f"accident; row says {detail.get('reasoning')!r}"
    )
