"""Skills: the registry check, and the receipt (Session 12).

A skill shapes how an answer is written, never what it may contain. So there is
exactly one boundary here to test — the boundary on the skill itself — and it is
tested the way every other boundary in this suite is: against the live stack,
with real tokens, through the same door the surfaces use.

Four cases, and the last is the one that matters most:

  * an unknown name is refused, so a caller cannot invent behaviour by asking
    for it, and the refusal is amber on the receipts page;
  * a real persona whose role the skill excludes is refused — since Session 13
    that is noor, and the exclusion is why demo moment 5 cannot be run in the
    configuration Session 12 measured as worse;
  * a token carrying a role the registry has never heard of is refused, the
    same boundary approached from the other side;
  * an authorized skill is accepted, and the audit row says which skills shaped
    the answer — a reply's register should be as recoverable afterwards as the
    tools behind it.

These tests do nothing when SKILLS_ENABLED is off, and say so rather than
failing: with the feature dark the field is meant to be inert, and a suite that
went red for a working kill switch would be pressure to leave it on.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import httpx
import pytest

from conftest import (
    CHAT_TIMEOUT_SECONDS,
    GATEWAY_URL,
    ORCHESTRATOR_URL,
    utcnow,
    wait_for_event,
)

pytestmark = pytest.mark.session2

# The one skill config/skills.yaml declares. Granted to advisor, dean and
# adjunct — and, since Session 13, not to faculty: see the unauthorized tests
# below and the comment on the roles line in the registry itself.
PLAIN_LANGUAGE = "plain_language"

# A role no persona holds and config/registry.yaml grants nothing to, for the
# second unauthorized case below.
UNGRANTED_ROLE = "registrar"


def post(
    client: httpx.Client,
    token: str,
    message: str,
    active_skills: list[str],
    *,
    base_url: str = ORCHESTRATOR_URL,
    timeout: float = 30.0,
) -> httpx.Response:
    return client.post(
        f"{base_url}/chat",
        json={"message": message, "history": [], "active_skills": active_skills},
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def skills_enabled(http: httpx.Client, token_for: Callable[[str], str]) -> bool:
    """Whether the running orchestrator has the feature on.

    Probed rather than read from the environment: the tests talk to a container,
    and the container's setting is the one that decides. An unknown skill is
    refused when the feature is on and silently ignored when it is off, and the
    difference is visible in one cheap request that never reaches a model.
    """
    response = post(http, token_for("pat"), "hello", ["no_such_skill_exists"])
    return response.status_code == 200 and "no_such_skill_exists" in response.json()["reply"]


def test_an_unknown_skill_is_refused(
    session2_stack: None, skills_enabled: bool, http: httpx.Client,
    token_for: Callable[[str], str],
) -> None:
    """A caller cannot author behaviour by naming it.

    The instructions live in config/skills.yaml and never travel on the wire, so
    the worst an unknown name can do is name nothing — and it is refused rather
    than dropped, because an answer shaped differently from what was asked for,
    with nothing in the reply to say so, is the outcome worth avoiding.
    """
    if not skills_enabled:
        pytest.skip("SKILLS_ENABLED is off on the running orchestrator")
    # Audit timestamps are written to whole seconds, so a `since` taken a
    # moment before the request can still be later than the row it is looking
    # for. Two seconds of slack, the same as tests/test_auth.py.
    since = utcnow() - timedelta(seconds=2)
    response = post(http, token_for("dana"), "Which occupations are growing fastest?",
                    ["definitely_not_a_skill"])
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert "definitely_not_a_skill" in body["reply"], (
        f"the refusal should name the skill it refused: {body['reply']!r}"
    )
    assert body["tools_used"] == [], (
        f"a refused skill must stop the request before any tool runs: {body['tools_used']}"
    )

    row = wait_for_event(
        http,
        lambda event: (event.get("event") == "skill_refused"
                       and (event.get("detail") or {}).get("skill") == "definitely_not_a_skill"),
        since=since,
    )
    assert row is not None, "the refusal left no audit row"
    assert row["detail"]["reason"] == "unknown", row["detail"]
    # The audit page colours a row by detail.decision, so without this key the
    # refusal reads green and the "refused" chip cannot select it. Session 12
    # deviation 6, found after that session's measurement began and fixed here.
    assert row["detail"].get("decision") == "refused", (
        f"a refused skill must render amber on the audit page: {row['detail']}"
    )


def test_a_real_persona_whose_role_the_skill_excludes_is_refused(
    session2_stack: None, skills_enabled: bool, http: httpx.Client,
    token_for: Callable[[str], str],
) -> None:
    """The registry governs who may activate what, checked against the token.

    noor's own token, and the persona matters. Session 12 measured
    plain_language on demo moment 5 — noor asking about a section she does not
    teach — and found it made the model readier to answer than to fetch, so the
    tool-layer refusal that beat exists to produce went missing in two of five
    runs. Session 12 wrote the constraint into DEMO_VERIFICATION.md; Session 13
    dropped `faculty` from the skill's roles, which turns a documented
    constraint into one the registry enforces. This test is what says so, and
    it is the one that would fail if somebody put the role back.

    Until Session 13 no persona could be unauthorized for this skill — it was
    granted to all four data roles — so the boundary was only reachable with a
    minted token carrying an invented role. That case is worth keeping and
    stands below; this one is the boundary as a real caller meets it.
    """
    if not skills_enabled:
        pytest.skip("SKILLS_ENABLED is off on the running orchestrator")
    # Audit timestamps are written to whole seconds, so a `since` taken a
    # moment before the request can still be later than the row it is looking
    # for. Two seconds of slack, the same as tests/test_auth.py.
    since = utcnow() - timedelta(seconds=2)
    response = post(http, token_for("noor"), "Which occupations are growing fastest?",
                    [PLAIN_LANGUAGE])
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert PLAIN_LANGUAGE in body["reply"], (
        f"the refusal should name the skill it refused: {body['reply']!r}"
    )
    assert body["tools_used"] == [], body["tools_used"]

    row = wait_for_event(
        http,
        lambda event: (event.get("event") == "skill_refused"
                       and (event.get("detail") or {}).get("skill") == PLAIN_LANGUAGE),
        since=since,
    )
    assert row is not None, "the refusal left no audit row"
    assert row["detail"]["reason"] == "not_authorized", row["detail"]


def test_a_role_the_registry_has_never_heard_of_is_refused(
    session2_stack: None, skills_enabled: bool, http: httpx.Client,
    mint: Callable[..., str],
) -> None:
    """The same boundary from the other side: a role nothing grants anything to.

    The token is real — correctly signed, unexpired, correctly audienced, the
    same technique tests/test_auth.py uses for its claim-level cases — and it is
    refused on the one thing under test, which is that its roles are not among
    the skill's. Nothing is weakened anywhere.

    Kept alongside the noor case above because the two fail differently: this
    one breaks if `resolve` ever defaults an unrecognised role to permitted;
    that one breaks if somebody grants the skill back to faculty.
    """
    if not skills_enabled:
        pytest.skip("SKILLS_ENABLED is off on the running orchestrator")
    token = mint(claims={"roles": [UNGRANTED_ROLE]})
    # Audit timestamps are written to whole seconds, so a `since` taken a
    # moment before the request can still be later than the row it is looking
    # for. Two seconds of slack, the same as tests/test_auth.py.
    since = utcnow() - timedelta(seconds=2)
    response = post(http, token, "Which occupations are growing fastest?", [PLAIN_LANGUAGE])
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert PLAIN_LANGUAGE in body["reply"], (
        f"the refusal should name the skill it refused: {body['reply']!r}"
    )
    assert body["tools_used"] == [], body["tools_used"]

    row = wait_for_event(
        http,
        lambda event: (event.get("event") == "skill_refused"
                       and (event.get("detail") or {}).get("skill") == PLAIN_LANGUAGE),
        since=since,
    )
    assert row is not None, "the refusal left no audit row"
    assert row["detail"]["reason"] == "not_authorized", row["detail"]


def test_an_authorized_skill_is_accepted_and_named_on_the_receipt(
    session2_stack: None, skills_enabled: bool, http: httpx.Client,
    token_for: Callable[[str], str],
) -> None:
    """The whole path: gateway, orchestrator, a real tool call, and the receipt.

    Driven through the gateway rather than straight at the orchestrator, because
    the field has to survive the hop the surfaces actually make. pat asks the
    public-data question so the request runs a tool and returns an answer
    without touching anything a persona could be refused for.
    """
    if not skills_enabled:
        pytest.skip("SKILLS_ENABLED is off on the running orchestrator")
    # Audit timestamps are written to whole seconds, so a `since` taken a
    # moment before the request can still be later than the row it is looking
    # for. Two seconds of slack, the same as tests/test_auth.py.
    since = utcnow() - timedelta(seconds=2)
    response = http.post(
        f"{GATEWAY_URL}/chat",
        json={"message": "Which occupations are growing fastest?", "history": [],
              "active_skills": [PLAIN_LANGUAGE]},
        headers={"Authorization": f"Bearer {token_for('pat')}"},
        timeout=CHAT_TIMEOUT_SECONDS,
    )
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert body["reply"].strip(), "an accepted skill must still produce an answer"
    assert body["tools_used"], (
        "the question should have reached mcp-labor; a skill must not stop a "
        f"request it was allowed on: {body}"
    )

    def is_this_answer(event: dict[str, Any]) -> bool:
        return event.get("event") == "answer_returned" and event.get("sub") == "pat"

    row = wait_for_event(http, is_this_answer, since=since)
    assert row is not None, "no answer_returned row for the request just made"
    assert row["detail"].get("active_skills") == [PLAIN_LANGUAGE], (
        f"answer_returned must record which skills shaped the answer: {row['detail']}"
    )
