"""gateway — the front door (SPEC §4.2).

Session 1: echo mode. The token is validated for real; the reply is an echo.
Session 2 adds the router call and forwarding to the orchestrator, at the marked
place below.
"""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI
from harness_auth import Claims, audit_event, bearer_claims
from pydantic import BaseModel, Field

app = FastAPI(title="gateway")


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
    return {"status": "ok"}


@app.post("/chat", response_model=ChatReply)
async def chat(request: ChatRequest, claims: Claims = Depends(bearer_claims)) -> ChatReply:
    started = time.perf_counter()

    # The router is a triage nurse, not a judge. Enforcement lives in the MCP servers. Do not add authorization logic here.
    #
    # Session 2 lands here: the ROUTER_MODEL call classifying intent, the
    # courteous refusal path (audited as refused_at_gate), and forwarding
    # {message, history} to the orchestrator with this same Bearer token.
    reply = f"echo: {request.message}"

    await audit_event(
        "request_completed",
        sub=claims.sub,
        roles=claims.roles,
        detail={
            "intent": None,
            "mode": "echo",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        },
    )
    return ChatReply(reply=reply, tools_used=[])
