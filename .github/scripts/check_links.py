#!/usr/bin/env python3
"""Every relative Markdown link in a tracked .md file must resolve.

Broken links are invisible locally and obvious on GitHub, which is the worst
combination. Session 17 moved two documents out of the repository root; this is
what would have caught a missed reference.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
files = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True,
                       text=True, check=True).stdout.split()

broken = 0
for rel in files:
    path = ROOT / rel
    for text, target in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", path.read_text()):
        clean = target.split("#")[0].strip()
        if not clean or clean.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / clean).resolve().exists():
            print(f"::error file={rel}::broken link [{text}]({target})")
            broken += 1

print(f"{len(files)} markdown files checked, {broken} broken relative links")
sys.exit(1 if broken else 0)
