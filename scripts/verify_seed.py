#!/usr/bin/env python3
"""Check that scripts/seed.py still reproduces the committed databases.

The four databases in data/ are committed so a clone runs without a seed step,
and seed.py is the source of truth for what is in them. Those two facts can
drift apart silently: nothing fails if someone edits seed.py and forgets to
re-seed, or re-seeds and forgets to commit. This script is how you find out.

It never touches data/. It copies seed.py into a temporary directory, runs it
there, and compares every table logically — schema, row count, and an
order-independent digest of the contents. A byte-level diff of the .db files
would be useless: SQLite page allocation is not stable across rebuilds, so two
databases holding identical rows routinely differ as files.

Run: uv run scripts/verify_seed.py
Exit status 0 if they agree, 1 if they do not.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMMITTED = REPO / "data"
SEED = REPO / "scripts" / "seed.py"
DATABASES = ["colleague", "canvas", "kuali", "labor"]


def table_names(path: Path) -> list[str]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        return sorted(
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        )


def fingerprint(path: Path, table: str) -> tuple[str, int, str]:
    """Schema, row count, and a digest that does not depend on row order."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()[0]
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608 - name from sqlite_master
    blob = "\n".join(sorted(repr(row) for row in rows)).encode()
    return schema, len(rows), hashlib.sha256(blob).hexdigest()[:16]


def seed_into(directory: Path) -> None:
    """Run seed.py against `directory` instead of the repository's data/.

    seed.py resolves its output as <script>/../data, so putting a copy at
    <directory>/scripts/seed.py sends its output to <directory>/data.
    """
    scripts = directory / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(SEED, scripts / "seed.py")
    subprocess.run(
        [sys.executable, str(scripts / "seed.py")],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="harness-verify-seed-") as tmp:
        fresh = Path(tmp)
        seed_into(fresh)

        problems = 0
        for name in DATABASES:
            committed, generated = COMMITTED / f"{name}.db", fresh / "data" / f"{name}.db"
            if not committed.exists():
                print(f"MISSING  data/{name}.db is not present — nothing to compare")
                problems += 1
                continue

            committed_tables, generated_tables = table_names(committed), table_names(generated)
            if committed_tables != generated_tables:
                print(f"DRIFT    {name}: table set differs")
                print(f"         committed: {committed_tables}")
                print(f"         seed.py:   {generated_tables}")
                problems += 1
                continue

            for table in committed_tables:
                have, want = fingerprint(committed, table), fingerprint(generated, table)
                if have == want:
                    print(f"OK       {name}.{table:<24} {have[1]:>5} rows  {have[2]}")
                    continue
                problems += 1
                print(f"DRIFT    {name}.{table}")
                if have[0] != want[0]:
                    print(f"         schema, committed: {have[0]}")
                    print(f"         schema, seed.py:   {want[0]}")
                if have[1] != want[1]:
                    print(f"         rows: committed {have[1]}, seed.py {want[1]}")
                if have[2] != want[2]:
                    print(f"         contents: committed {have[2]}, seed.py {want[2]}")

    print()
    if problems:
        print(
            f"{problems} difference(s). Either re-run `uv run scripts/seed.py` and commit\n"
            "data/*.db, or fix seed.py so it produces what is committed."
        )
        return 1
    print("No drift: seed.py reproduces the committed databases exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
