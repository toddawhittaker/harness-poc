"""The orchestrator opens a connection only where the caller has a tool.

Session 2's verification run lost roughly one request in sixteen to an MCP
handshake that never completed — on a server whose tools the caller did not
even hold. The orchestrator built clients to all four servers on every request,
so one slow server could fail a question that needed none of it.

Two claims are checked here, and they are different claims:

1. Every server serves exactly the tools the orchestrator's SERVER_TOOLS map
   says it does. Drift there is silent: a tool listed under the wrong server
   makes the right server go undialled and the answer read like missing data.
2. A request opens connections only to servers holding a tool the caller holds.
   pat is an adjunct with two labor tools, so pat's request must never reach for
   the student record system at all — least exposure first, smaller failure
   surface second.

Claim 2 is asserted from the audit row, because the audit row is the artifact
the demo puts on screen. `servers` next to `tools_offered` is the registry-
filtering claim in machine-readable form.
"""

from __future__ import annotations

import httpx
import pytest

from conftest import (
    CHAT_TIMEOUT_SECONDS,
    MCP_SERVERS,
    ORCHESTRATOR_URL,
    mcp_session,
    post_chat_with_token,
    utcnow,
    wait_for_event,
)

pytestmark = pytest.mark.session2

# Deliberately a second, independent copy of the map in
# services/orchestrator/app.py. If it were imported, a wrong edit there would
# make this test agree with the mistake. Written out, the two have to be wrong
# in the same way at the same time to pass, and the live servers below have to
# be wrong too.
EXPECTED_TOOLS: dict[str, set[str]] = {
    "mcp-colleague": {
        "get_my_advisees", "get_student_summary", "get_program_summaries",
        "get_enrollment_trends", "get_student_degree_progress", "get_next_term_options",
    },
    "mcp-canvas": {
        "get_my_sections", "get_section_engagement", "get_program_engagement_rollup",
    },
    "mcp-kuali": {
        "get_program_curriculum", "get_course_outcomes", "list_programs_catalog",
    },
    "mcp-labor": {
        "list_occupations", "get_occupation", "get_program_occupation_map",
    },
}

# Which servers each persona's roles can reach, given the registry in
# config/registry.yaml. The interesting entries are the absences.
EXPECTED_SERVERS: dict[str, list[str]] = {
    "pat": ["labor"],                            # adjunct: public data only
    "noor": ["canvas", "kuali", "labor"],        # faculty: no student record system
    "dana": ["colleague", "kuali", "labor"],     # advisor: no section engagement
    "kim": ["colleague", "canvas", "kuali", "labor"],   # dean: all four
}


@pytest.mark.parametrize("server", sorted(EXPECTED_TOOLS))
def test_each_server_advertises_exactly_the_tools_the_orchestrator_expects(
    session2_stack: None, dana_token: str, server: str,
) -> None:
    with mcp_session(MCP_SERVERS[server], dana_token) as session:
        advertised = session.list_tools()
    assert advertised == EXPECTED_TOOLS[server], (
        f"{server} advertises {sorted(advertised)}; SERVER_TOOLS in "
        f"services/orchestrator/app.py expects {sorted(EXPECTED_TOOLS[server])}. "
        "A tool filed under the wrong server makes the right one go undialled."
    )


@pytest.mark.parametrize("persona", ["pat", "noor"])
def test_a_request_reaches_only_the_servers_the_callers_roles_can_use(
    session2_stack: None, http: httpx.Client, token_for, persona: str,
) -> None:
    since = utcnow()
    token = token_for(persona)
    # Straight at the orchestrator, so the gateway's triage cannot decide this
    # for us: the connection decision under test is the orchestrator's own.
    response = post_chat_with_token(
        http, token,
        message="What is the fastest growing occupation?",
        base_url=ORCHESTRATOR_URL,
        timeout=CHAT_TIMEOUT_SECONDS,
    )
    assert response.status_code == 200, response.text[:300]

    row = wait_for_event(
        http,
        lambda event: (
            event.get("service") == "orchestrator"
            and event.get("event") == "answer_returned"
            and event.get("sub") == persona
        ),
        since=since,
        timeout=15.0,
    )
    assert row is not None, f"no orchestrator answer_returned row for {persona}"
    servers = row["detail"].get("servers")
    assert servers == EXPECTED_SERVERS[persona], (
        f"{persona} reached {servers}; expected {EXPECTED_SERVERS[persona]}"
    )

    # Every answer also says whether a handshake had to be retried. The field is
    # normally empty; it exists so a flake nobody can see afterwards does not
    # become a flake nobody fixes — the failure mode Session 2 hit and could
    # only diagnose from container logs.
    assert "reconnected" in row["detail"], (
        f"orchestrator row {row['id']} does not say whether a handshake was retried"
    )
