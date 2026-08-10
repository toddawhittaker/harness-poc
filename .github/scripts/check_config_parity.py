#!/usr/bin/env python3
"""Every ${VAR} docker-compose.yml uses must be documented in .env.example.

A variable that compose reads and the template never mentions is a deployment
that works on the machine it was written on and nowhere else. Session 17's LXC
rehearsal failed on exactly that class of gap.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

compose = set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)", (ROOT / "docker-compose.yml").read_text()))
template = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", (ROOT / ".env.example").read_text(), re.M))

missing = sorted(compose - template)
unused = sorted(template - compose)

for name in missing:
    print(f"::error::docker-compose.yml reads ${{{name}}} but .env.example never documents it")
for name in unused:
    print(f"::warning::.env.example documents {name}, which docker-compose.yml never reads")

print(f"{len(compose)} variables in compose, {len(template)} in the template, {len(missing)} missing")
sys.exit(1 if missing else 0)
