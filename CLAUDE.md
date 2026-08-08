# harness-poc
POC of a university AI harness. Master spec: SPEC.md — follow it; where code
and spec conflict, the spec wins; where the spec is silent, choose the boring option.
Production vision: ARCHITECTURE.md — read it before proposing any design not
covered by SPEC.md, and decide in its spirit; for the POC, SPEC.md always wins.

## Commands
- run all: docker compose up --build
- seed:    uv run scripts/seed.py
- tests:   uv run pytest tests/ -x -q   (stack must be running)
- one svc: docker compose up gateway --build

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
