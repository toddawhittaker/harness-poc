"""Shared model construction for harness-poc (SPEC §1).

Shared *code*, like harness_auth — not a shared runtime. Import the factory,
never build a model client yourself.
"""

from .factory import (
    AGENT_MODEL,
    AGENT_SETTINGS,
    AGENT_THINKING,
    ROUTER_MODEL,
    ROUTER_SETTINGS,
    ROUTER_THINKING,
    UsageStats,
    agent_model,
    router_model,
    usage_stats,
)

__all__ = [
    "AGENT_MODEL",
    "AGENT_SETTINGS",
    "AGENT_THINKING",
    "ROUTER_MODEL",
    "ROUTER_SETTINGS",
    "ROUTER_THINKING",
    "UsageStats",
    "agent_model",
    "router_model",
    "usage_stats",
]
