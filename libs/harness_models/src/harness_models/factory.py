"""The one place model clients are built (SPEC §1).

Two services call models: the gateway (the router, on ROUTER_MODEL) and the
orchestrator (the agent, on AGENT_MODEL). Both get their model from here, fully
configured. No call site anywhere passes a base URL, an API key, a model name,
or a thinking-mode setting — if you find yourself wanting to, the setting
belongs in this file instead.

That rule is not tidiness. Model configuration drifting between two call sites
is how one service quietly ends up in thinking mode, paying reasoning-token
prices and a second of latency, while the demo blames the network.
"""

from __future__ import annotations

import os

from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", "deepseek-v4-flash")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "deepseek-v4-pro")

# Extended-reasoning mode, one flag per model. ONE FLAG PER MODEL IS THE POINT:
# a single flag governing both is how Session 10's A/B nearly measured one thing
# and shipped another. That session ran the agent in reasoning mode by
# recreating only the orchestrator, so the gateway's router kept the value it
# was built with and stayed non-thinking — which is what the numbers describe.
# With one shared flag, a later `docker compose up -d` would have put the router
# into reasoning mode too, silently, and nobody would have been measuring that.
#
# SPEC §1 mandates non-thinking for both, and both ship that way. Session 11
# tried the agent with reasoning ON and reverted it: it does remove the
# arithmetic defect class (0 of 10 runs wrong, against 5 of 10), and it also
# costs demo moment 5b its tool-layer refusal about half the time, because a
# model that has already reasoned over the section list answers from the list
# instead of calling the tool that would refuse. SPEC §1 and docs/LESSONS.md
# entries 5 and 9 record both halves.
#
# The switch is DeepSeek's top-level `thinking` object — {"type": "enabled" |
# "disabled"} — documented in the create-chat-completion request schema at
# api-docs.deepseek.com. It defaults to "enabled" server-side, so non-thinking
# is something we must send, not something we get by saying nothing.
#
# Pydantic AI has no named setting for it (it is provider-specific), so it
# rides in ModelSettings.extra_body, which the OpenAI-compatible model forwards
# verbatim into the request body. Note there is no `openai_chat_extra_body`
# setting despite what older snippets suggest; `extra_body` on the base
# ModelSettings is the field.
def _thinking(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


AGENT_THINKING = _thinking("AGENT_THINKING", "false")
ROUTER_THINKING = _thinking("ROUTER_THINKING", "false")


def _settings(thinking: bool) -> ModelSettings:
    return ModelSettings(
        extra_body={"thinking": {"type": "enabled" if thinking else "disabled"}}
    )


AGENT_SETTINGS = _settings(AGENT_THINKING)
ROUTER_SETTINGS = _settings(ROUTER_THINKING)


def _model(name: str, settings: ModelSettings) -> OpenAIChatModel:
    """One DeepSeek model client, settings baked in.

    Settings are attached to the model object rather than passed at each
    `agent.run(...)`, so a call site cannot forget them or override them by
    accident.
    """
    return OpenAIChatModel(
        name,
        provider=OpenAIProvider(base_url=BASE_URL, api_key=API_KEY),
        settings=settings,
    )


def router_model() -> OpenAIChatModel:
    """The gateway's triage model (SPEC §4.2). Reads ROUTER_THINKING only."""
    return _model(ROUTER_MODEL, ROUTER_SETTINGS)


def agent_model() -> OpenAIChatModel:
    """The orchestrator's execution model (SPEC §4.3). Reads AGENT_THINKING only."""
    return _model(AGENT_MODEL, AGENT_SETTINGS)


class UsageStats(BaseModel):
    """What one model call cost, in the shape the audit detail records.

    HOW TO READ THESE NUMBERS. DeepSeek bills cache hits at roughly a fiftieth
    of cache misses, so the hit/miss split is the number that says whether
    prompt-cache discipline (SPEC §1: static prefixes, dynamic content in
    messages after them) is actually holding.

    Reason about cache behaviour ONLY from prompt_cache_hit_tokens and
    prompt_cache_miss_tokens — never from prompt_tokens. deepseek-v4-flash
    prepends its own prompt server-side, so prompt_tokens does not equal the
    tokens we sent, and inferring "the prefix must have changed" from a moved
    prompt_tokens count will send you hunting a bug that is not there. The
    hit/miss fields describe the cache directly; the totals do not.

    A second identical question reporting zero hits means dynamic content
    contaminated a static prefix. That is a build failure, not a footnote.
    """

    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def usage_stats(usage: object) -> UsageStats:
    """Read a Pydantic AI RunUsage into UsageStats.

    DeepSeek's two cache counters arrive only inside the usage `details`
    mapping — Pydantic AI's own `cache_read_tokens` field stays zero for this
    provider, because it is populated from the nested cache shapes Anthropic
    and OpenAI use. Reading the wrong field yields a confident, permanent zero,
    which would make the cache check in the demo verifier meaningless.

    Every read is defensive: a provider that omits a field must produce a zero,
    never an exception on the audit path.
    """
    details = getattr(usage, "details", None) or {}
    return UsageStats(
        prompt_cache_hit_tokens=int(details.get("prompt_cache_hit_tokens", 0)),
        prompt_cache_miss_tokens=int(details.get("prompt_cache_miss_tokens", 0)),
        prompt_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "output_tokens", 0) or 0),
    )
