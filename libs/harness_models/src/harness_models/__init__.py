"""Shared model construction for harness-poc (SPEC §1).

Shared *code*, like harness_auth — not a shared runtime. Import the factory,
never build a model client yourself.
"""

from .factory import (
    AGENT_MODEL,
    MODEL_SETTINGS,
    ROUTER_MODEL,
    UsageStats,
    agent_model,
    router_model,
    usage_stats,
)

__all__ = [
    "AGENT_MODEL",
    "MODEL_SETTINGS",
    "ROUTER_MODEL",
    "UsageStats",
    "agent_model",
    "router_model",
    "usage_stats",
]
