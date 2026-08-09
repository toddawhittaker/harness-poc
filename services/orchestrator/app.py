"""orchestrator — the harness, always live (SPEC §4.3).

A service, not a library: the agent loop runs here, behind an HTTP contract, and
the surfaces above it hold no logic. That is what makes "one harness, many
doors" true rather than aspirational.

Four things happen on every request, in this order:

1. The token is verified here, independently. The gateway already did it. That
   is the point — this service is reachable directly, and SPEC §7 step 4 is a
   live demonstration of someone doing exactly that.
2. The caller's roles are mapped to a tool allowlist from config/registry.yaml.
3. MCP clients are built for all four servers, carrying the CALLER's bearer
   token, and filtered to the allowlist BEFORE the agent is constructed — a
   tool this role cannot use is never in the model's view, not merely refused
   when called.
4. The agent runs against a static system prompt with every dynamic thing after
   it, and every tool call and the final answer are audited.

The harness holds no credentials of its own. Every tool call downstream happens
as the person who asked, and no further.
"""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from harness_auth import Claims, audit_event, bearer_claims
from harness_models import agent_model, usage_stats
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ToolCallPart
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.tools import ToolDefinition

from prompts import SYSTEM_PROMPT
from registry import allowed_tools

app = FastAPI(title="orchestrator")

# The four governed integrations. Names match the citation markers in the system
# prompt and the `service` field the servers audit under.
MCP_SERVERS: dict[str, str] = {
    "colleague": os.environ.get("MCP_COLLEAGUE_URL", "http://mcp-colleague:8021/mcp"),
    "canvas": os.environ.get("MCP_CANVAS_URL", "http://mcp-canvas:8023/mcp"),
    "kuali": os.environ.get("MCP_KUALI_URL", "http://mcp-kuali:8024/mcp"),
    "labor": os.environ.get("MCP_LABOR_URL", "http://mcp-labor:8022/mcp"),
}

# A wrong question should fail in seconds, not hang a demo.
MCP_INIT_TIMEOUT = 10.0
MCP_READ_TIMEOUT = 60.0


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


def toolsets(token: str, allowed: set[str]) -> list[MCPToolset]:
    """One filtered MCP client per server, carrying the caller's own token.

    Per-request construction, which costs roughly 100ms across four servers.
    Accepted at POC scale, and noted here rather than optimised: a pooled client
    would have to be keyed by token to stay correct, and getting that wrong is
    how one user's connection serves another user's request.

    `.filtered` runs at tool-listing time, so a tool outside the allowlist never
    reaches the model's schema — it is invisible, not merely forbidden.
    """
    def permitted(ctx: RunContext[None], tool: ToolDefinition) -> bool:
        return tool.name in allowed

    return [
        MCPToolset(
            url,
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
        for url in MCP_SERVERS.values()
    ]


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

    agent = Agent(
        agent_model(),
        instructions=SYSTEM_PROMPT,
        toolsets=toolsets(bearer_token(http_request), allowed),
    )

    try:
        result = await agent.run(
            caller_context(claims, request.message),
            message_history=message_history(request.history),
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
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1)},
        )
        raise HTTPException(
            status_code=502,
            detail="The harness could not complete that request. Please try again.",
        ) from exc

    # Read back what the model actually called. Reporting intent instead of
    # fact would let tools_used disagree with the audit trail, and the audit
    # trail is the one that has to be true.
    tools_used: list[str] = []
    for message in result.all_messages():
        for part in message.parts:
            if isinstance(part, ToolCallPart) and part.tool_name not in tools_used:
                tools_used.append(part.tool_name)

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
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            **usage.model_dump(),
        },
    )
    return ChatReply(reply=result.output, tools_used=tools_used)
