"""orchestrator — the harness, always live (SPEC §4.3).

A service, not a library: the agent loop runs here, behind an HTTP contract, and
the surfaces above it hold no logic. That is what makes "one harness, many
doors" true rather than aspirational.

Four things happen on every request, in this order:

1. The token is verified here, independently. The gateway already did it. That
   is the point — this service is reachable directly, and SPEC §7 step 4 is a
   live demonstration of someone doing exactly that.
2. The caller's roles are mapped to a tool allowlist from config/registry.yaml.
3. MCP clients are built — carrying the CALLER's bearer token — only for the
   servers still holding a tool after the allowlist is applied, and filtered to
   the allowlist BEFORE the agent is constructed. A tool this role cannot use is
   never in the model's view, not merely refused when called; a server whose
   every tool this role lacks is never dialled at all.
4. The agent runs against a static system prompt with every dynamic thing after
   it, and every tool call and the final answer are audited.
5. The answer is checked against the tools that actually ran before it is
   returned (grounding.py). SPEC §4.3 tells the model to answer only from tool
   results; this is the part that does not take its word for it.

The harness holds no credentials of its own. Every tool call downstream happens
as the person who asked, and no further.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import AsyncExitStack
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from harness_auth import Claims, audit_event, bearer_claims
from harness_models import agent_model, usage_stats
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ToolCallPart
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import AbstractToolset

import grounding
from prompts import SYSTEM_PROMPT
from registry import allowed_tools, registry_tools

log = logging.getLogger("orchestrator")

app = FastAPI(title="orchestrator")

# The four governed integrations. Names match the citation markers in the system
# prompt and the `service` field the servers audit under.
MCP_SERVERS: dict[str, str] = {
    "colleague": os.environ.get("MCP_COLLEAGUE_URL", "http://mcp-colleague:8021/mcp"),
    "canvas": os.environ.get("MCP_CANVAS_URL", "http://mcp-canvas:8023/mcp"),
    "kuali": os.environ.get("MCP_KUALI_URL", "http://mcp-kuali:8024/mcp"),
    "labor": os.environ.get("MCP_LABOR_URL", "http://mcp-labor:8022/mcp"),
}

# Which server holds which tool (SPEC §4.4–§4.7). Known here, before any
# connection is opened, because the decision this drives is whether to open one
# at all: an adjunct's question has no business dialling the student record
# system, and a connection never opened cannot fail, cannot time out, and cannot
# be the subject of an argument about what it might have returned.
#
# tests/test_orchestrator_connections.py asks each live server for its own tool
# list and fails if this map has drifted from it.
SERVER_TOOLS: dict[str, frozenset[str]] = {
    "colleague": frozenset({
        "get_my_advisees", "get_student_summary", "get_program_summaries",
        "get_enrollment_trends", "get_student_degree_progress", "get_next_term_options",
    }),
    "canvas": frozenset({
        "get_my_sections", "get_section_engagement", "get_program_engagement_rollup",
    }),
    "kuali": frozenset({
        "get_program_curriculum", "get_course_outcomes", "list_programs_catalog",
    }),
    "labor": frozenset({
        "list_occupations", "get_occupation", "get_program_occupation_map",
    }),
}

# A wrong question should fail in seconds, not hang a demo.
MCP_INIT_TIMEOUT = 10.0
MCP_READ_TIMEOUT = 60.0

# One retry, then give up. Roughly one handshake in sixteen failed during
# Session 2's verification run, and the one observed failure succeeded
# immediately on a second attempt — so a single retry is worth having and a
# retry loop is not. Short enough that a genuinely dead server still fails the
# request in seconds rather than hanging the demo.
MCP_CONNECT_ATTEMPTS = 2
MCP_CONNECT_BACKOFF = 0.25

# The corrective instruction for an ungrounded reply. It is sent as a TRAILING
# message on the second run — never merged into SYSTEM_PROMPT, and never
# rendered into the prefix. The prefix has to stay byte-identical or every
# request after this one is a cache miss (SPEC §1), and a guard that quietly
# cost the demo its prompt cache would be a poor trade for a rare correction.
#
# It names the fault and then restates the requirement, because "that was
# wrong" without the requirement invites a differently-wrong second attempt.
REGROUND_INSTRUCTION = (
    "That reply is not grounded in this request's tool results: {problem}\n\n"
    "Answer the question again from scratch. Use only names, ids and numbers "
    "that a tool returned in this conversation; cite each fact to the server "
    "whose tool returned it; and if the tools cannot ground an answer, say that "
    "in one flat sentence and stop rather than supplying figures. Do not "
    "mention this correction or apologise for the first reply."
)

# What the caller gets when the second attempt is ungrounded too. One sentence,
# courteous, and it promises nothing: SPEC §4.3's "if tools can't ground the
# answer, say so and stop", said by the service rather than by the model.
UNGROUNDED_REPLY = "I can't ground an answer to that with the tools available."

# How many attempts the guard allows. One regeneration, then the flat sentence:
# a loop here would turn a bad answer into a slow bad answer.
GROUNDING_ATTEMPTS = 2


def _check_every_registry_tool_has_a_server() -> None:
    """Fail at import rather than answer a question with a tool silently missing.

    If a tool is in registry.yaml but in no server's list here, no client would
    be built for it and the model would simply never see it — an answer that
    looks like a limitation of the data rather than a typo in a map. Loud is
    better.
    """
    served = set().union(*SERVER_TOOLS.values())
    for name, tools in SERVER_TOOLS.items():
        others = set().union(*(t for other, t in SERVER_TOOLS.items() if other != name))
        assert not (tools & others), f"{name} shares a tool name with another server"
    orphans = registry_tools() - served
    if orphans:
        raise RuntimeError(
            f"registry.yaml grants tools no MCP server claims: {sorted(orphans)}. "
            "Add them to SERVER_TOOLS or remove them from the registry."
        )


_check_every_registry_tool_has_a_server()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = Field(default_factory=list)


class ChatReply(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness only: no auth, no downstream calls.

    Deliberately says nothing about whether the MCP servers or the model
    endpoint are reachable. A readiness probe that fans out turns one sick
    dependency into an entire stack marked unhealthy, and during a demo the
    difference between "the orchestrator is down" and "labor data is down" is
    the difference between a pause and a panic.
    """
    return {"status": "ok"}


def bearer_token(request: Request) -> str:
    """The caller's raw token, to be forwarded to the MCP servers.

    Read from the header rather than re-signed or re-minted: the token that
    arrives is the token that travels. `bearer_claims` has already verified it
    by the time any handler runs, so this cannot hand a bad token onward.
    """
    return (request.headers.get("authorization") or "").partition(" ")[2].strip()


def reachable_servers(allowed: set[str]) -> list[str]:
    """The servers this caller has at least one tool on, in MCP_SERVERS order.

    pat holds two labor tools and nothing else, so pat's requests name exactly
    one server here and never open a connection to mcp-colleague at all.
    """
    return [name for name, tools in SERVER_TOOLS.items() if tools & allowed]


def build_toolset(name: str, token: str, allowed: set[str]) -> AbstractToolset[None]:
    """One filtered MCP client, carrying the caller's own token.

    Per-request construction, which costs roughly 100ms per server. Accepted at
    POC scale, and noted here rather than optimised: a pooled client would have
    to be keyed by token to stay correct, and getting that wrong is how one
    user's connection serves another user's request.

    `.filtered` runs at tool-listing time, so a tool outside the allowlist never
    reaches the model's schema — it is invisible, not merely forbidden.
    """
    def permitted(ctx: RunContext[None], tool: ToolDefinition) -> bool:
        return tool.name in allowed

    return MCPToolset(
        MCP_SERVERS[name],
        auth=token,
        init_timeout=MCP_INIT_TIMEOUT,
        read_timeout=MCP_READ_TIMEOUT,
        # An authorization refusal is not something to have another go at.
        # The default, 'retry', hands the refusal back to the model framed
        # as "self-correct and try again" — which invites precisely the
        # working-around that ground rule 3 forbids, and burns the retry
        # budget until the run raises. 'failed' shows the model the refusal
        # as a result, so it can do the one correct thing: relay it.
        tool_error_behavior="failed",
    ).filtered(permitted)


async def connect_toolsets(
    stack: AsyncExitStack, token: str, allowed: set[str], retried: list[str],
) -> list[AbstractToolset[None]]:
    """Open a session to each reachable server, retrying a failed handshake once.

    The handshake is opened here rather than left to `agent.run` so the retry can
    be aimed at the one thing that flakes. Retrying the whole run would re-drive
    the model and could repeat tool calls that already happened.

    A fresh client per attempt: the failed one has already unwound its own exit
    stack, and reusing a half-built session to save an object is exactly the kind
    of cleverness this codebase is meant not to have. Servers that retried are
    named in `retried`, which lands in the audit detail — a flake nobody can see
    afterwards is a flake nobody will fix.
    """
    live: list[AbstractToolset[None]] = []
    for name in reachable_servers(allowed):
        for attempt in range(1, MCP_CONNECT_ATTEMPTS + 1):
            try:
                live.append(await stack.enter_async_context(
                    build_toolset(name, token, allowed)))
                break
            except Exception as exc:  # noqa: BLE001 — retried, then re-raised below
                if attempt == MCP_CONNECT_ATTEMPTS:
                    raise
                log.warning("mcp %s handshake failed (%s); retrying once",
                            name, type(exc).__name__)
                retried.append(name)
                await asyncio.sleep(MCP_CONNECT_BACKOFF)
    return live


def message_history(history: list[Message]) -> list[Any]:
    """Prior turns, as messages after the static prefix.

    The harness is stateless; the client holds the conversation and hands it
    back each time. Anything unrecognised is dropped rather than guessed at.
    """
    messages: list[Any] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        elif turn.role in {"assistant", "model"}:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def tools_called(result: Any) -> list[str]:
    """Which tools the model actually called, in call order, deduplicated.

    Read back from the run rather than tracked as intent: reporting intent
    would let `tools_used` disagree with the audit trail, and the audit trail is
    the one that has to be true. On a regenerated run the history carries both
    attempts, so this is every tool that ran during the whole request — which is
    exactly the set the grounding check has to be judged against.
    """
    called: list[str] = []
    for message in result.all_messages():
        for part in message.parts:
            if isinstance(part, ToolCallPart) and part.tool_name not in called:
                called.append(part.tool_name)
    return called


def servers_reached(tools: list[str]) -> set[str]:
    """The servers behind a list of called tools — the guard's ground truth."""
    called = set(tools)
    return {name for name, owned in SERVER_TOOLS.items() if owned & called}


def caller_context(claims: Claims, message: str) -> str:
    """Who is asking and what they asked — dynamic, so it goes AFTER the prefix.

    This is the string that must never migrate into prompts.SYSTEM_PROMPT. It
    changes on every request, and a static prefix containing it is a static
    prefix in name only.
    """
    roles = ", ".join(claims.roles) or "no data roles"
    return f"Asked by {claims.name} (roles: {roles}).\n\n{message}"


@app.post("/chat", response_model=ChatReply)
async def chat(
    request: ChatRequest,
    http_request: Request,
    claims: Claims = Depends(bearer_claims),
) -> ChatReply:
    started = time.perf_counter()
    allowed = allowed_tools(claims.roles)
    retried: list[str] = []
    regenerated = False
    declined = False

    try:
        async with AsyncExitStack() as stack:
            agent = Agent(
                agent_model(),
                instructions=SYSTEM_PROMPT,
                toolsets=await connect_toolsets(
                    stack, bearer_token(http_request), allowed, retried),
            )
            result = await agent.run(
                caller_context(claims, request.message),
                message_history=message_history(request.history),
            )

            # The groundedness guard (SPEC §4.3). Inside the stack because the
            # second attempt needs the same live MCP sessions — the point of
            # regenerating is that the model can call the tool it skipped.
            for attempt in range(1, GROUNDING_ATTEMPTS + 1):
                called = tools_called(result)
                verdict = grounding.check(result.output, servers_reached(called))
                if verdict.ok:
                    break
                last = attempt == GROUNDING_ATTEMPTS
                await audit_event(
                    "answer_ungrounded", sub=claims.sub, roles=claims.roles,
                    detail={
                        "attempt": attempt,
                        # The offending markers, so the audit page says which
                        # claim of provenance was false and not merely that one
                        # was. Empty when the reply cited nothing and asserted
                        # figures anyway — there is no marker to name.
                        "markers": list(verdict.markers),
                        "reason": verdict.reason,
                        "tools_used": called,
                        "outcome": "declined" if last else "regenerating",
                    },
                )
                if last:
                    declined = True
                    break
                regenerated = True
                result = await agent.run(
                    REGROUND_INSTRUCTION.format(problem=verdict.reason),
                    message_history=result.all_messages(),
                )
    except Exception as exc:  # noqa: BLE001 — every outcome leaves a receipt
        # Without this, a model timeout or an unreachable MCP server is a bare
        # 500 and the audit page has nothing to say about it. Every other
        # outcome in this system leaves a row, and the one the audit page cannot
        # explain is the worst one to be missing in front of a room.
        #
        # The class name only: the message can carry a row of student data or a
        # URL with a query string.
        await audit_event(
            "answer_failed", sub=claims.sub, roles=claims.roles,
            detail={"reason": type(exc).__name__,
                    "tools_offered": sorted(allowed),
                    "servers": reachable_servers(allowed),
                    "reconnected": retried,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1)},
        )
        raise HTTPException(
            status_code=502,
            detail="The harness could not complete that request. Please try again.",
        ) from exc

    tools_used = tools_called(result)
    # The model's text is dropped when the guard declined it, and the tool rows
    # below are still written: the calls happened, and a request that produced
    # an answer nobody may read is exactly the one the audit page should show.
    reply = UNGROUNDED_REPLY if declined else result.output

    for name in tools_used:
        # The MCP server audits this call too, under its own service name. Two
        # rows, deliberately: independent records from independent enforcement
        # layers. Do not "deduplicate" them — see rules.py in any mcp-* service.
        await audit_event(
            "tool_call", sub=claims.sub, roles=claims.roles,
            detail={"tool": name, "via": "orchestrator"},
        )

    usage = usage_stats(result.usage)
    await audit_event(
        "answer_returned", sub=claims.sub, roles=claims.roles,
        detail={
            "tools_used": tools_used,
            "tools_offered": sorted(allowed),
            # Which servers this caller's roles even reached for. Next to
            # tools_offered it is the registry-filtering claim in machine-
            # readable form: pat's row names one server, and it is not the
            # student record system.
            "servers": reachable_servers(allowed),
            "reconnected": retried,
            # Whether the groundedness guard fired, and whether it had to give
            # up. Normally both false, and a row where they are not is the one
            # worth looking at.
            "regenerated": regenerated,
            "ungrounded": declined,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            **usage.model_dump(),
        },
    )
    return ChatReply(reply=reply, tools_used=tools_used)
