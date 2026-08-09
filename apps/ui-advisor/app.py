"""Advisor Workspace — one of two doors onto the same harness (SPEC §4.9).

Everything below the branding block is wiring. The behaviour lives in
harness_chat.py, which is byte-identical to the copy in apps/ui-exec: the two
apps differ in palette and copy and in nothing else, because "same harness,
same second, different room" is the claim demo moments 1 and 2 make side by
side.

Any persona can sign in here. Access follows the token's roles, not the door.
"""

from __future__ import annotations

import chainlit as cl
from harness_chat import Branding, answer, authenticate, start_chat, starters

BRAND = Branding(
    name="Advisor Workspace",
    greeting=(
        "Welcome, {who}. This is the **Advisor Workspace** — ask about your "
        "advisees, their progress, and what they should take next term. "
        "Answers come from the university's systems of record, and every "
        "question is on the audit record."
    ),
    starters=[
        ("Who is struggling",
         "Which students seem to be struggling this term?"),
        ("Next term",
         "What should S-1055 take next term?"),
        ("Where the jobs are",
         "Which occupations are growing fastest?"),
    ],
)


@cl.password_auth_callback
async def password_auth(username: str, password: str) -> cl.User | None:
    return await authenticate(username, password)


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return starters(BRAND)


@cl.on_chat_start
async def on_chat_start() -> None:
    await start_chat(BRAND)


@cl.on_message
async def on_message(message: cl.Message) -> None:
    await answer(message)
