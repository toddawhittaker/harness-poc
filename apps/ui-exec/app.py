"""Executive Insights — the other door onto the same harness (SPEC §4.9).

Everything below the branding block is wiring. The behaviour lives in
harness_chat.py, which is byte-identical to the copy in apps/ui-advisor: the
two apps differ in palette and copy and in nothing else, because "same harness,
same second, different room" is the claim demo moments 1 and 2 make side by
side.

Any persona can sign in here. Access follows the token's roles, not the door —
signing pat in here during Q&A is the cleanest way to show it.
"""

from __future__ import annotations

import chainlit as cl
from harness_chat import Branding, answer, authenticate, start_chat, starters

BRAND = Branding(
    name="Executive Insights",
    greeting=(
        "Welcome, {who}. This is **Executive Insights** — ask about programs, "
        "enrollment, engagement across the institution, and how the catalog "
        "lines up with the labor market. Every question is on the audit record."
    ),
    starters=[
        ("Who is struggling",
         "Which of my advisees seem to be struggling this term?"),
        ("Engagement this week",
         "How's engagement across all programs this week?"),
        ("Qualification",
         "Which fast-growing occupations would a Cybersecurity BS graduate qualify for?"),
        ("Catalog gaps",
         "Which fast-growing occupations have no matching program in our catalog — "
         "what could we consider rolling out?"),
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
