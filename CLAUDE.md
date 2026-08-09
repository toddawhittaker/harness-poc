# harness-poc

POC of a university AI harness. Master spec: SPEC.md — follow it; where code
and spec conflict, the spec wins; where the spec is silent, choose the boring option.
Production vision: ARCHITECTURE.md — read it before proposing any design not
covered by SPEC.md, and decide in its spirit; for the POC, SPEC.md always wins.

## Commands

- run all: docker compose up --build
- seed:    uv run scripts/seed.py
           then: docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
           The servers hold the deleted database file open until they are
           restarted, so without this you keep reading the old data.
- tests:   uv run pytest tests/ -x -q   (stack must be running)
- one svc: docker compose up gateway --build
- pre-demo: docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
Expect "clean". Run it AFTER the test suite, never during: the disruptive
test stops the audit service on purpose, so a run within 30 minutes of the
suite shows an expected auth_failed drop from the gateway. Anything else
means demo moment 9's audit page will be missing rows; the line names the
service and the URL that failed. Drops are debounced to once a minute per
process, so one line can stand for several lost events.

## Deploy (LXC, tunnel profile)

git pull && docker compose --profile tunnel up -d

Set real values for CHAINLIT_AUTH_SECRET_ADVISOR and CHAINLIT_AUTH_SECRET_EXEC
in .env on the LXC. The built-in defaults are fine on localhost and nowhere
else: they sign each Chainlit app's session cookie, and a public tunnel plus a
published cookie secret is a forgeable login. They have no bearing on the
harness JWTs, which identity-stub signs with RS256.

## Hard rules

- Never weaken, mock, or bypass JWT validation — not in dev mode, not in tests,
not "temporarily". Tests use real tokens from identity-stub.
- Every service validates tokens independently via libs/harness_auth. No service
trusts upstream validation.
- Authorization decisions live ONLY in MCP servers (+ registry filtering in the
orchestrator). Never add them to the gateway or UIs.
- Model system prompts are static string constants. Dynamic content goes in
messages after the prefix (DeepSeek prefix caching).
- Python 3.12, uv, type hints everywhere, Pydantic models for every payload.
- Small files, no cleverness. This is a demo that must be readable on a projector.
- At session start, before any other work: if `SESSION_REPORT.md` exists, move  it to reports/session-&lt;n&gt;.md (next unused n) and commit that move by  itself. Then, at every plan-approval pause, stop-point question, and  session end, write your full report to `SESSION_REPORT.md` (overwrite, never  append): what was done, any deviations and why, acceptance status per  criterion, open questions. Then halt. The report must stand alone — it  will be reviewed by someone with no access to this terminal, so include  the evidence (commands run, outputs, counts), not just conclusions.

