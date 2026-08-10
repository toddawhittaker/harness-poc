## What this changes, and why

<!-- One paragraph. What a reader needs to judge the change, not a diff summary. -->

## Evidence

<!-- Commands run and their output. This repository's convention is that a claim
     without evidence is a guess — see any report in reports/. -->

- [ ] `ruff check` clean (CI proves it)
- [ ] Nothing in `data/`, `.env`, or any key is committed (gitleaks proves it)
- [ ] `docker compose build` succeeds (CI proves it)

If this touches `services/`, `libs/`, `config/` or `scripts/`:

- [ ] Full suite run and green — `gh workflow run "Full suite (live stack)"`, result linked below
- [ ] If seed data or `scripts/seed.py` changed: `uv run scripts/verify_seed.py` clean and `data/*.db` re-committed

## Effect on the certified record

<!-- docs/DEMO_VERIFICATION.md's current certificate describes a specific
     configuration. Say which of these applies. -->

- [ ] No effect — documentation, CI, or a surface the certification never exercised
- [ ] Changes behaviour the certificate describes, and the certificate says so / needs re-running

## Merge

Do not merge this yourself. Leave it for the repository owner, per `CLAUDE.md`.
