"""gateway — the front door (SPEC §4.2).

Verifies the caller's token, triages the question with a small fast model, and
forwards the survivors to the orchestrator with the same bearer token. It holds
no authorization logic and no model config of its own: models come from
harness_models, enforcement lives in the MCP servers.
"""

from __future__ import annotations

import os
import time

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from harness_auth import Claims, audit_event, bearer_claims
from harness_models import router_model, usage_stats
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from prompts import ROUTER_PROMPT

app = FastAPI(title="gateway")

ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8010/chat")

# The agent loop behind this can run several tool calls; give it room. The
# router's own budget is much smaller — a triage step that takes ten seconds has
# already failed at its job.
ORCHESTRATOR_TIMEOUT = 120.0
ROUTER_TIMEOUT = 15.0

# One retry, then fail open (SPEC §4.2). See the note at `triage`.
ROUTER_ATTEMPTS = 2


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = Field(default_factory=list)
    # Carried, not read. The surfaces send the skills a user switched on and the
    # orchestrator validates them against config/skills.yaml and the caller's
    # roles; the gateway forwards the names untouched and makes no judgement
    # about them, exactly as it makes none about the tools below it.
    active_skills: list[str] = Field(default_factory=list)


class ChatReply(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


class RouterDecision(BaseModel):
    """The router's verdict. Strict schema — the model fills exactly this."""

    intent: str
    in_scope: bool
    plausibly_authorized: bool
    refusal_message: str | None = None


# Built once. The prompt is static and the model carries its own settings, so
# there is nothing per-request to configure.
router_agent = Agent(
    router_model(),
    output_type=RouterDecision,
    instructions=ROUTER_PROMPT,
    retries=1,
)

# What the router is told when it cannot be trusted to have spoken. Not a
# refusal — an explicit decision to let the layers below do their job.
FAIL_OPEN = RouterDecision(
    intent="unclassified", in_scope=True, plausibly_authorized=True, refusal_message=None
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


async def triage(claims: Claims, message: str) -> tuple[RouterDecision, bool]:
    """Classify one question. Returns the verdict and whether the router spoke.

    Retry once, then fail open. Failing open is safe here precisely because the
    gateway is not the enforcement point: a question waved through still meets
    registry filtering at the orchestrator and independent authorization at every
    MCP server. Failing *closed* would mean a flaky model endpoint could deny
    people access to their own data, which is a worse failure and a less honest
    one.

    Note this covers the router being unable to answer — a timeout, a malformed
    response, a schema the model would not fill. It does not cover the router
    answering "not authorized", which is a verdict and is honoured below.
    """
    # Dynamic content, after the static prefix — never inside it.
    roles = ", ".join(claims.roles) or "no data roles"
    prompt = f"Asker's roles: {roles}\n\nQuestion: {message}"

    for attempt in range(ROUTER_ATTEMPTS):
        try:
            result = await router_agent.run(prompt)
        except Exception as exc:  # noqa: BLE001 — any failure to classify is the same failure
            if attempt + 1 < ROUTER_ATTEMPTS:
                continue
            await audit_event(
                "router_parse_failed",
                sub=claims.sub,
                roles=claims.roles,
                detail={"reason": type(exc).__name__, "attempts": ROUTER_ATTEMPTS,
                        "action": "failed open — enforcement continues below"},
            )
            return FAIL_OPEN, False
        else:
            usage = usage_stats(result.usage)
            await audit_event(
                "router_classified", sub=claims.sub, roles=claims.roles,
                detail={"intent": result.output.intent, "in_scope": result.output.in_scope,
                        "plausibly_authorized": result.output.plausibly_authorized,
                        **usage.model_dump()},
            )
            return result.output, True

    return FAIL_OPEN, False  # unreachable; keeps the type honest


@app.post("/chat", response_model=ChatReply)
async def chat(
    request: ChatRequest,
    http_request: Request,
    claims: Claims = Depends(bearer_claims),
) -> ChatReply:
    started = time.perf_counter()

    # The router is a triage nurse, not a judge. Enforcement lives in the MCP servers. Do not add authorization logic here.
    decision, routed = await triage(claims, request.message)

    refused = routed and (not decision.in_scope or not decision.plausibly_authorized)
    if refused:
        reply = decision.refusal_message or (
            "I can't help with that one. Ask me about something your role covers "
            "and I'll do what I can."
        )
        await audit_event(
            "refused_at_gate", sub=claims.sub, roles=claims.roles,
            detail={"intent": decision.intent, "in_scope": decision.in_scope,
                    "plausibly_authorized": decision.plausibly_authorized,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1)},
        )
        return ChatReply(reply=reply, tools_used=[])

    # The caller's own token travels on, unchanged. The gateway never mints a
    # token of its own and never calls downstream as itself.
    authorization = http_request.headers.get("authorization") or ""
    async with httpx.AsyncClient(timeout=ORCHESTRATOR_TIMEOUT) as client:
        response = await client.post(
            ORCHESTRATOR_URL,
            json={"message": request.message,
                  "history": [turn.model_dump() for turn in request.history],
                  "active_skills": request.active_skills},
            headers={"Authorization": authorization},
        )

    if response.status_code == 401:
        # The orchestrator validates independently and disagreed with us. Its
        # verdict wins: relay the 401 rather than papering over it.
        #
        # Audited here as well as there. The orchestrator writes its own
        # auth_failed, but without this row the audit page shows a 401
        # attributed only to the orchestrator for a request that entered
        # through the front door — and the two layers disagreeing about a token
        # is exactly the event someone reading that page needs to see from both
        # sides.
        await audit_event(
            "auth_failed", sub=claims.sub, roles=claims.roles,
            detail={"reason": "orchestrator rejected a token the gateway accepted",
                    "intent": decision.intent},
        )
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    response.raise_for_status()
    body = response.json()

    await audit_event(
        "request_completed", sub=claims.sub, roles=claims.roles,
        detail={"intent": decision.intent, "routed": routed,
                "tools_used": body.get("tools_used", []),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1)},
    )
    return ChatReply(reply=body.get("reply", ""), tools_used=body.get("tools_used", []))
