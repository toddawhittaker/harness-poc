"""Role to tool mapping, read from config/registry.yaml (SPEC §4.3).

This is registry FILTERING, not enforcement. It decides what the model can see;
the MCP servers decide what anyone can have. Both matter, for different reasons:
filtering keeps the model from being tempted by, and then refused on, tools it
was never going to be allowed to call, which keeps answers clean and token
counts down. Enforcement is what holds when the filtering is wrong, absent, or
bypassed entirely — which is the demo.

If this file and an MCP server ever disagree, the MCP server is right.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

REGISTRY_PATH = Path(os.environ.get("REGISTRY_PATH", "/config/registry.yaml"))


@lru_cache(maxsize=1)
def _roles() -> dict[str, list[str]]:
    document = yaml.safe_load(REGISTRY_PATH.read_text()) or {}
    roles = document.get("roles") or {}
    return {role: list(tools) for role, tools in roles.items()}


def allowed_tools(roles: list[str]) -> set[str]:
    """The union of tools these roles may use.

    A union, not an intersection: someone holding advisor and dean reaches
    everything either role reaches. A role the registry does not list
    contributes nothing rather than raising — an unknown role is a caller who
    sees no tools, which is the safe direction to fail.
    """
    registry = _roles()
    return {tool for role in roles for tool in registry.get(role, [])}
