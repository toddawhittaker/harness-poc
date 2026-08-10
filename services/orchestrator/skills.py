"""Skills — governed behavioral configuration, read from config/skills.yaml.

A skill is a named block of instructions that shapes how an answer is written.
It is *governed* in four specific senses, and each one is a deliberate contrast
with "paste some extra prompt text in":

1. It exists in a registry. A caller cannot invent a skill by naming one; a
   name that is not in config/skills.yaml is refused, the same way a tool that
   is not in config/registry.yaml is not offered.
2. It is role-gated. Each skill names the roles that may activate it, checked
   against the caller's own verified token — the same check registry.py makes
   for tools, in the same place, against the same claims.
3. It is injected as a TRAILING message, never merged into the system prompt.
   The prefix is what DeepSeek caches (SPEC §1); a skill that rewrote it would
   quietly turn every request into a cache miss.
4. It is visible in the audit trail. `answer_returned` carries active_skills,
   so a reply's register is as recoverable afterwards as the tools behind it.

What a skill is NOT, and must never become: an authorization decision. Nothing
here can widen what a caller may see. That lives in the MCP servers, which
re-check every call against the same token and know nothing about this file.
The one boundary this module enforces is the boundary on the skill itself.

`SKILLS_ENABLED` is the kill switch. Off, this module is inert: /chat validates
nothing, ignores nothing, and writes no skills field, so the request path is the
one that was certified before the feature existed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

SKILLS_PATH = Path(os.environ.get("SKILLS_PATH", "/config/skills.yaml"))

# Default on, so the demo can toggle a skill without an env change. Off makes
# the feature dark rather than partially applied — see the module docstring.
SKILLS_ENABLED = os.environ.get("SKILLS_ENABLED", "true").strip().lower() not in {
    "0", "false", "no", "off", "",
}

# The only activation the POC implements. The registry field carries the others
# (role-default, surface-default, model-invoked) so they are an extension rather
# than a redesign; a skill declaring one of them would need code that does not
# exist here, so it is refused at load rather than silently treated as `user`.
SUPPORTED_ACTIVATIONS = frozenset({"user"})


@dataclass(frozen=True)
class Skill:
    name: str
    roles: frozenset[str]
    activation: str
    description: str
    instructions: str


class SkillRefused(Exception):
    """A requested skill the caller may not have, or that does not exist.

    Carries the courteous sentence the caller sees and the machine-readable
    reason the audit row records. Both, because the demo needs the first and the
    receipts need the second.
    """

    def __init__(self, skill: str, reason: str, message: str) -> None:
        super().__init__(message)
        self.skill = skill
        self.reason = reason
        self.message = message


@lru_cache(maxsize=1)
def catalog() -> dict[str, Skill]:
    """Every skill the registry declares, by name.

    Missing file means no skills, not a crash: the feature is additive, and an
    orchestrator that refused to start because a style registry was absent would
    be a worse failure than one that offers nothing.
    """
    if not SKILLS_PATH.is_file():
        return {}
    document = yaml.safe_load(SKILLS_PATH.read_text()) or {}
    skills: dict[str, Skill] = {}
    for entry in document.get("skills") or []:
        name = str(entry["name"])
        activation = str(entry.get("activation", "user"))
        if activation not in SUPPORTED_ACTIVATIONS:
            raise RuntimeError(
                f"skill {name!r} declares activation {activation!r}; this POC implements "
                f"{sorted(SUPPORTED_ACTIVATIONS)} only. Add the code before the registry entry."
            )
        skills[name] = Skill(
            name=name,
            roles=frozenset(entry.get("roles") or []),
            activation=activation,
            description=str(entry.get("description", "")),
            instructions=str(entry.get("instructions", "")).strip(),
        )
    return skills


def resolve(names: list[str], roles: list[str]) -> list[Skill]:
    """The skills this caller asked for and may have, in the order asked.

    Raises on the first name that is unknown or not this caller's to activate.
    Refusing the whole request rather than dropping the offending name is the
    honest behaviour: silently ignoring half of what was asked for would give
    the caller an answer whose shape they did not choose and cannot see.
    """
    held = set(roles)
    known = catalog()
    chosen: list[Skill] = []
    for name in names:
        if name in {skill.name for skill in chosen}:
            continue
        skill = known.get(name)
        if skill is None:
            raise SkillRefused(
                name, "unknown",
                f"There is no “{name}” mode available here, so I have not applied it. "
                "Ask again without it and I will answer normally.",
            )
        if not (skill.roles & held):
            raise SkillRefused(
                name, "not_authorized",
                f"The “{name}” mode is not available to your role, so I have not "
                "applied it. Ask again without it and I will answer normally.",
            )
        chosen.append(skill)
    return chosen


def skill_message(skills: list[Skill]) -> str | None:
    """The one trailing message carrying every active skill's instructions.

    One message rather than one per skill, so the shape of the conversation the
    model sees does not change with the number of skills switched on. None when
    nothing is active, which is what keeps the no-skills request path identical
    to the one that was certified.
    """
    if not skills:
        return None
    return "\n\n".join(skill.instructions for skill in skills)
