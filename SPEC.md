# harness-poc — Build Specification

A proof-of-concept of the Franklin University AI Harness, buildable by one person in 2–3 days using Claude Code. This document is the master spec: hand it to Claude Code and build in the stage order of §12.

## Why this exists (read first)

This POC is a working miniature of a production system described in ARCHITECTURE.md: a single, institution-owned AI layer — the harness — that sits above Franklin University's real systems (Canvas, Colleague, Kuali, labor-market data), answers questions in plain language for people in different roles, and enforces the university's access rules at every step. The production design has one organizing principle, and the POC inherits it unchanged: **the user's own identity travels with every request, end to end, and authorization is checked independently at multiple layers.** The AI never acts as an all-seeing service account, and no model's judgment is ever the security boundary.

Every stand-in here maps to something real, and the mapping is the point: the identity-stub stands in for Microsoft Entra ID; token pass-through stands in for the on-behalf-of exchange; the four mock MCP servers stand in for governed integrations with real institutional systems; the two Chainlit apps stand in for many thin surfaces multiplexed over one always-live service. When you face a decision this spec doesn't settle, decide as if the production system were watching: enforcement stays in the tool servers, surfaces stay thin and hold no logic, the harness stays a running service (never a library embedded in apps), dynamic context never contaminates a static prompt prefix, and everything leaves an audit trail. The demo exists to prove the *shape* is sound — one harness multiplexing many apps, many sources, and many roles, with no component trusting another's say-so.

## 0. What this POC must prove (and nothing else)

Four demo claims, in demo order:

1. **Multiplexing** — two visually distinct chat apps drive one always-live harness service.
2. **RBAC** — the same question yields role-appropriate answers, refusals happen politely at the gate, and — the money shot — bypassing the gate entirely (curl straight to the orchestrator with a low-privilege token) is *still* blocked at the MCP layer. Layered enforcement, demonstrated live.
3. **Synthesis** — one question is answered by joining independent data sources (four available: record, engagement, curriculum, labor market), with citations to each.
4. **Receipts** — an audit viewer shows every request: who, which role, which tools fired, what was refused.

**Fake the providers, keep the mechanisms real.** Identities are fake personas, but they mint real RS256-signed JWTs validated by signature at every service. Data is fake, but tools, transport (MCP over streamable HTTP), and per-request authorization are real. Anything that would invalidate the architectural claim if faked must not be faked.

Out of scope, deliberately: writes, small-cell suppression, streaming-token UX polish, persistence of chat history across restarts, tests beyond the negative-auth set and demo verifier, TLS inside the compose network (the tunnel terminates TLS).

## 1. Stack (pin these)

- Python 3.12 everywhere. Package management with `uv` (one `pyproject.toml` per service, `uv.lock` committed).
- FastAPI + uvicorn for gateway, identity-stub, audit.
- Pydantic AI (latest stable) for the orchestrator agent.
- MCP Python SDK (latest stable), FastMCP servers, **streamable HTTP transport**.
- PyJWT[crypto] for RS256 sign/verify. httpx for service-to-service calls.
- SQLite (stdlib sqlite3 is fine; keep it synchronous and simple) for seed data and audit.
- Chainlit (latest 2.x) for both UIs.
- Docker Compose v2. One `docker-compose.yml`, dev-mode volume mounts for hot reload (`--reload` for uvicorn, `chainlit run -w`).
- cloudflared as an optional compose profile (`--profile tunnel`).
- MCP Python SDK pinned `>=1.29,<2` (the FastMCP API; 1.x is in maintenance mode, and that stability is deliberate for this POC — do not upgrade to 2.x or substitute standalone fastmcp). Streamable HTTP transport.

Models via env, OpenAI-compatible endpoint:

```
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
ROUTER_MODEL=deepseek-v4-flash
AGENT_MODEL=deepseek-v4-pro
```

Pydantic AI: construct with the OpenAI-compatible model class pointed at `DEEPSEEK_BASE_URL`. Non-thinking mode by default for both (demo latency matters); `AGENT_THINKING=false` env flag to flip later.

**Prompt-cache discipline (applies to every model call):** DeepSeek caches by exact prompt prefix automatically. Therefore: system prompts are static strings — no f-strings interpolating user, date, or role into them. Tool schemas registered in a fixed, sorted order. All dynamic context (persona name, roles, the user's question) enters as messages *after* the static prefix. This is a hard rule; the auth-reviewer agent checks it.

## 2. Repository layout (monorepo)

```
harness-poc/
├── CLAUDE.md
├── SPEC.md                    # this document
├── ARCHITECTURE.md            # the production vision — context, not contract
├── .claude/agents/            # §13
├── docker-compose.yml
├── .env.example
├── libs/
│   └── harness_auth/          # shared: JWT verify, audit client (tiny)
│       ├── pyproject.toml
│       └── src/harness_auth/{__init__.py, jwt.py, audit.py}
├── services/
│   ├── identity-stub/
│   ├── gateway/
│   ├── orchestrator/
│   ├── mcp-colleague/
│   ├── mcp-canvas/
│   ├── mcp-kuali/
│   ├── mcp-labor/
│   └── audit/
├── apps/
│   ├── ui-advisor/            # Chainlit, theme A
│   └── ui-exec/               # Chainlit, theme B
├── config/
│   ├── registry.yaml          # role → allowed tools
│   └── personas.yaml
├── scripts/
│   ├── seed.py                # deterministic fake data → data/*.db
│   └── demo_bypass.sh         # the curl-the-orchestrator attack
├── data/                      # gitignored; sqlite files land here (volume)
└── tunnel/config.yml          # cloudflared ingress
```

`libs/harness_auth` is shared *code*, not a shared runtime — every service still validates independently. It exports: `verify_token(token) -> Claims` (fetches/caches JWKS from identity-stub, checks signature, iss, aud, exp; raises on any failure) and `audit_event(**fields)` (fire-and-forget POST to audit service; never blocks or crashes the caller on failure).

## 3. Identity: personas and tokens

`config/personas.yaml`:

```yaml
personas:
  dana:  { name: "Dana Whitfield", password: "demo", roles: [advisor] }
  kim:   { name: "Kim Okafor",     password: "demo", roles: [dean] }
  noor:  { name: "Noor Haddad",    password: "demo", roles: [faculty] }   # teaches two sections
  pat:   { name: "Pat Reyes",      password: "demo", roles: [adjunct] }  # no data roles
  sam:   { name: "Sam Lindqvist",  password: "demo", roles: [advisor, dean] }  # keep in reserve for Q&A
```

JWT claims: `iss=http://identity-stub:8001`, `aud=harness-poc`, `sub` (persona id), `name`, `roles` (list), `iat`, `exp` (+8h). RS256; keypair generated at identity-stub first boot into the `data/` volume so tokens survive restarts.

**The token is passed through end to end**: UI → gateway → orchestrator → MCP servers, in the `Authorization: Bearer` header at every hop. Each service validates independently. (This pass-through *simulates* the production on-behalf-of exchange; swapping the stub for Entra changes the issuer and adds token exchange — the enforcement code stays.)

## 4. Services

### 4.1 identity-stub (:8001)
FastAPI. Endpoints: `GET /personas` (ids + display names, no passwords); `POST /token` `{persona, password}` → `{access_token}` or 401; `GET /jwks.json`. ~120 lines. No audit calls (pre-identity).

### 4.2 gateway (:8000) — the front door
FastAPI. One endpoint that matters: `POST /chat` `{message: str, history: [{role, content}]}` with Bearer token.

Flow: (1) `verify_token` → 401 on failure, audited as `auth_failed`. (2) **Router call** on `ROUTER_MODEL`: static system prompt instructing strict-JSON output with schema `{intent: str, in_scope: bool, plausibly_authorized: bool, refusal_message: str|null}`; the message-after-prefix contains the roles list and the user question. Router knows only the *category* map (which roles can plausibly reach which intent categories: advisee_detail→advisor, program_aggregate→dean, labor_market→any, other→refuse). Parse defensively; on malformed JSON, retry once, then treat as in_scope (fail open at the gate — the layers below are the enforcement; leave a `router_parse_failed` audit event). (3) If refused: return the courteous refusal, audit `refused_at_gate`. (4) Else forward `{message, history}` to orchestrator with the same Bearer; stream/relay the reply. (5) Audit `request_completed` with intent and latency.

**Comment in code, verbatim:** `# The router is a triage nurse, not a judge. Enforcement lives in the MCP servers. Do not add authorization logic here.`

### 4.3 orchestrator (:8010) — the harness, always live
FastAPI wrapping a Pydantic AI agent. `POST /chat`, same contract as gateway.

Flow: (1) `verify_token` independently (yes, again — that's the point). (2) Load `config/registry.yaml`; compute the union of tools allowed for the caller's roles. (3) Construct MCP clients (streamable HTTP) for all four MCP servers — colleague, canvas, kuali, labor — **with the caller's Bearer in the connection headers** — per-request construction is acceptable at POC scale; note the ~100ms cost and move on. (4) Filter the toolsets to the allowed list before handing them to the agent — a tool the role can't use is never visible to the model. (5) Run the agent: static system prompt (institutional analyst persona; answer only from tool results; cite every fact as `[colleague]` / `[labor]`; if tools can't ground the answer, say so and stop; if a tool refuses, relay the refusal politely — never work around it). Dynamic context (name, roles, question, history) after the prefix. (6) Return `{reply, tools_used: [...]}`. Audit `tool_call` per tool invocation (name, args hash, ok/refused) and `answer_returned`.

`registry.yaml`:

```yaml
roles:
  advisor: [get_my_advisees, get_student_summary, get_student_degree_progress, get_next_term_options,
            get_program_curriculum, list_occupations, get_occupation, get_program_occupation_map]
  faculty: [get_my_sections, get_section_engagement, get_program_curriculum, get_course_outcomes,
            list_occupations, get_occupation]
  dean:    [get_program_summaries, get_enrollment_trends, get_section_engagement, get_program_engagement_rollup,
            get_program_curriculum, get_course_outcomes, list_programs_catalog,
            list_occupations, get_occupation, get_program_occupation_map]
  adjunct: [list_occupations, get_occupation]   # public data only — makes the contrast visible
```

### 4.4 mcp-colleague (:8021) — fake SIS, real enforcement
FastMCP, streamable HTTP, SQLite from seed. Middleware on every request: extract Bearer → `verify_token` → stash claims in context; 401 (and audit `auth_failed`) on failure. **This server trusts nothing upstream.**

Tools (typed args and returns; raise a tool error with a clear, user-relayable message on authorization failure — the orchestrator's model will repeat it, which is fine and demo-visible):

- `get_my_advisees()` — requires role `advisor`; returns advisees assigned to `sub` in the advisor_assignments table: id, name, program, current_courses, last_login_days, gpa, term_grade_flags. Refuses (not empties) for non-advisors: "requires the advisor role."
- `get_student_summary(student_id)` — requires `advisor` AND the student assigned to `sub`. An advisor asking about someone else's advisee gets: "Student S-1042 is not among your assigned advisees." A dean gets: "Individual student records require an advisor assignment; deans receive aggregates." (This line *is* the RBAC demo — make it exact.)
- `get_program_summaries()` — requires `dean`; per-program: headcount, avg GPA, % students with last_login_days > 10.
- `get_enrollment_trends(program_code=None)` — requires `dean`; four fake terms of headcounts.
- `get_student_degree_progress(student_id)` — requires `advisor` + assignment; completed courses and credits against program requirements, prereqs satisfied.
- `get_next_term_options(student_id)` — requires `advisor` + assignment; remaining required courses whose prereqs are met, flagged by which are offered next term. (This tool is Colleague's reason to exist in the demo: the system of record answers *what should happen next term*; Canvas answers *what is happening this week*.)

Every tool call audited: `tool=..., sub=..., roles=..., decision=ok|refused`.

### 4.5 mcp-labor (:8022) — fake BLS/O*NET
Same skeleton, same per-request token validation (public *data*, but identical *mechanism* — say this in the demo). Tools, allowed to all authenticated roles: `list_occupations(sort_by_growth: bool = True)`; `get_occupation(soc_code)` → title, growth_pct, median_wage, skills[]; `get_program_occupation_map()` → program_code ↔ soc_codes.

### 4.6 mcp-canvas (:8023) — fake LMS, the current-data source
Same skeleton as mcp-colleague (per-request token validation, audit, SQLite from seed). Canvas is the *pulse*: this-week activity, keyed to the same student ids as colleague so cross-source joins work. Tools:

- `get_my_sections()` — requires role `faculty`; sections where `sub` is the instructor (via the faculty_assignments table): section id, course, enrollment, this-week login %, missing-submission count.
- `get_section_engagement(section_id)` — `faculty`: own sections only; a cross-section ask refuses with exactly: "Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean." `dean`: any section. Returns per-student rows: id, name, last_login_days, submitted, missing.
- `get_program_engagement_rollup(program_code=None)` — requires `dean`; per-program current-week engagement aggregates. (Faculty see their rooms; the dean sees the building — this asymmetry is demo moment 5.)

### 4.7 mcp-kuali (:8024) — fake curriculum
Same skeleton, same per-request validation. Low-sensitivity data, but identical mechanism. Tools (advisor, faculty, dean):

- `get_program_curriculum(program_code)` — required courses, sequence, prereqs.
- `get_course_outcomes(program_code)` — learning outcomes per course, each tagged with skill keywords. **The skill tags share one controlled vocabulary with mcp-labor's occupation skills (see §5)** — this shared vocabulary is what makes the qualification and gap-analysis syntheses land as real joins rather than fuzzy vibes.
- `list_programs_catalog()` — all programs with codes (dean; the left side of the gap analysis).

### 4.8 audit (:8030) — the receipts
FastAPI + SQLite (own file). `POST /events` accepts:

```json
{ "ts": "...", "service": "gateway|orchestrator|mcp-colleague|mcp-labor",
  "event": "auth_failed|refused_at_gate|router_parse_failed|tool_call|answer_returned|request_completed",
  "sub": "dana", "roles": ["advisor"], "detail": { } }
```

`GET /events?limit=100` newest-first. `GET /` serves one self-contained HTML page (vanilla JS, 2-second polling, monospace table, color-code: green ok / amber refused / red auth_failed). No framework, no build step. This page is on screen for demo moment 4 — make the columns readable from the back of a room: time, service, event, who, roles, detail.

### 4.9 ui-advisor (:8080) and ui-exec (:8081)
Two Chainlit apps, ~80 lines each, differing only in theme and header copy ("Advisor Workspace" warm palette / "Executive Insights" cool palette — divergence is the point; use Chainlit theming, don't fight it). `@cl.password_auth_callback` → POST identity-stub `/token` → stash JWT in the user session. Each message: POST gateway `/chat` with Bearer and the session's running history (client-held history keeps the harness stateless). Render `tools_used` as a subtle suffix line. **Any persona can log into either app** — access follows the token's roles, not the app. Log pat into the exec app during Q&A to prove it.

### 4.10 cloudflared (profile: tunnel)
`tunnel/config.yml` ingress: `advisor.<domain>` → ui-advisor:8080, `exec.<domain>` → ui-exec:8081, `audit.<domain>` → audit:8030, catch-all 404. Chainlit uses websockets; tunnel passes them through — no special config. Compose service uses `TUNNEL_TOKEN` env. Everything must also work on plain localhost ports with the profile off; develop local, deploy to the LXC by `git pull && docker compose --profile tunnel up -d`.

## 5. Seed data (`scripts/seed.py`)

Deterministic (`random.seed(398)`), writes `data/colleague.db`, `data/canvas.db`, `data/kuali.db`, and `data/labor.db`. Define one module-level `SKILLS` list (~40 controlled-vocabulary skill strings: "network defense", "incident response", "financial analysis", "SQL", "cloud architecture", …) and draw *both* Kuali outcome tags and labor occupation skills from it — exact-string overlap is what makes the qualification and gap syntheses provably real.

**Colleague** (the record): 6 programs (CS-BS, IS-MS, CYB-BS, DAT-MS, BUS-BS, HIM-BS with CIP-like codes); 300 students with **boring realistic names** (no jokes — the room must stay on the argument); assignments: dana → 25 advisees, two fictional advisors take the rest; per student: gpa (skewed normal), last_login_days (mostly 0–5, a deliberate tail of 8 students >10 among dana's advisees — the demo depends on this), completed courses/credits, current registrations, term_grade_flags. Plus per-program degree requirements with prereq chains and a next-term course schedule, tuned so at least three of dana's advisees have a clean, interesting next-term answer (one blocked by an unmet prereq).

**Canvas** (the pulse): current-term sections for the same courses, instructor assignments (noor teaches CYB-310-A and CYB-210-A, and deliberately no BUS section — see below; fictional instructors take the rest), and per-student weekly activity keyed to the *same student ids* as colleague: last_login_days, submitted, missing. Make CYB-310-A visibly healthy and BUS-201-B visibly not, so the two ends of the range are on the record; noor's own sections are CYB-310-A and CYB-210-A, and her own-section answer should have texture. Noor must hold no section whose id is adjacent to BUS-201-A: demo moment 5 needs her refused for that section, and a near-identical id of her own gives the model something it may read and answer about instead.

**Kuali** (the curriculum): per program, required course sequence with prereqs, and per course 3–5 outcomes tagged with SKILLS entries. Tune CYB-BS outcomes to strongly cover Information Security Analysts' skills and partially cover two others — the qualification demo should show a strong match, a partial match, and a miss.

**Labor** (the market): 12 SOC-coded occupations with growth_pct, median_wage, 5–8 SKILLS-drawn skills each; program→occupation map for every program. Make the top-3 by growth: Information Security Analysts (mapped, strong CYB match), plus **two deliberately unmapped fast-growers** — "AI/ML Engineers" and "Cloud Infrastructure Architects" — whose skills partially overlap existing CS/DAT outcomes. These two are the whole gap-analysis demo: fast growth, no program in the catalog, credible adjacency.

Idempotent: delete and recreate all four on each run.

## 6. Negative-auth tests (the only mandatory test file)

`tests/test_auth.py`, runnable with `uv run pytest` against the live compose stack: no token → 401 at gateway, orchestrator, and all four MCP servers (six services, independently). Expired token → 401. Tampered signature → 401. Wrong `aud` → 401. pat's valid token calling `get_my_advisees` directly on mcp-colleague → tool-level refusal. dana's token requesting a student not assigned to dana → refusal message names the boundary. noor's token calling `get_section_engagement` for a section noor doesn't teach → refusal naming the boundary; kim's token, same call → succeeds (the faculty/dean asymmetry, proven at the tool layer). These tests are written (by the auth-reviewer agent) *before* the auth code is finished, and they gate every stage.

## 7. Demo script (~14 minutes full; cut line marked for a 10-minute slot)

1. Both UIs side by side. Dana in Advisor Workspace: *"Which students seem to be struggling this term?"* → her 25 — the only students her tools reach — the quiet ones flagged, cited `[colleague]`.
2. Kim in Executive Insights, **the same words** → program aggregates, no individual names. The question carries no possessive, so neither answer has to argue with it; the role alone decides the scope. Same harness, same second.
3. Pat in Executive Insights, same question → courteous gate refusal. Then Pat: *"Which occupations are growing fastest?"* → answered. Roles gate data, not curiosity.
4. **The bypass.** `scripts/demo_bypass.sh` on screen: mints pat's token, curls the orchestrator directly — "suppose someone sweet-talks or skips the AI gate" — mcp-colleague refuses; the refusal lands amber in the audit view. One command, whole thesis.
5. **Faculty vs dean.** Noor: *"How is my CYB-310 section doing this week?"* → live-ish engagement, `[canvas]`. Noor: *"And how's BUS-201-A doing?"* → refused by name — not her section. Kim: *"How's engagement across all programs this week?"* → the rollup. Faculty see their rooms; the dean sees the building.
6. **Record vs pulse** *(cut first if time is short)*. Dana: *"What should S-1055 take next term?"* → degree progress, prereqs met, next-term offerings, `[colleague]`. Canvas knows this week; Colleague knows what comes next — different questions, different sources, one harness.
7. **Qualification synthesis.** Kim: *"Which fast-growing occupations would a Cybersecurity BS graduate qualify for?"* → CYB outcomes' skills matched against occupation skills: a strong match, a partial, a miss — `[kuali]` and `[labor]` interleaved.
8. **Gap synthesis.** Kim: *"Which fast-growing occupations have no matching program in our catalog — what could we consider rolling out? Check each program in our catalog."* → AI/ML Engineers and Cloud Infrastructure Architects surface, with the adjacent existing outcomes noted, and a claim that a skill is missing across the catalog is made only after every program's outcomes have been fetched. The room realizes it's watching program strategy, not IT.
9. Audit page full-screen. Scroll the session just performed — refusals, the bypass, every tool, every role. "Every question, every refusal, on the record. This is the FERPA story."
10. Close with the honesty slide: fake identities and data; real tokens, validation, gate, agent loop, tool layer, audit. "This was days one through three of the six-week MVP plan."

If the slot is 10 minutes: cut 6, and run 7 and 8 as one two-question beat.

## 8. Build order for Claude Code (three sessions)

- **Session 1 — skeleton + identity.** Repo layout, compose with identity-stub, gateway (echo, no router), audit + viewer, `harness_auth`, seed script. Auth-reviewer writes `tests/test_auth.py` first; then wire validation until green. *Exit: signed-in curl round-trips through gateway; audit rows visible; all negative tests pass.*
- **Session 2 — MCP + orchestrator.** All four MCP servers with per-request validation and tool rules — build mcp-colleague completely first, then stamp mcp-canvas, mcp-kuali, and mcp-labor from its skeleton (they differ only in tools and rules; this is an hour each of agent work, not a day); orchestrator with Pydantic AI, registry filtering, header-borne token; router into gateway. *Exit: `demo_bypass.sh` blocked at MCP; dana/kim/pat/noor curls produce demo answers 1–7; cache discipline verified (static prefixes).*
- **Session 3 — surfaces + polish.** Both Chainlit apps, themes, citations suffix, audit page readability, seed-data tuning so demo answers are crisp, tunnel profile, rehearse the script twice end to end. *Exit: the §7 script runs clean on the LXC via the tunnel.*

## 9. Claude Code configuration

### CLAUDE.md (create at repo root, this content)

```markdown
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
```

### .claude/agents/auth-reviewer.md
```markdown
---
name: auth-reviewer
description: Reviews all token/auth code; writes negative tests first. Use before and after any change touching JWT, headers, middleware, or personas.
---
You are a skeptical security reviewer for harness-poc. Scope: identity-stub,
libs/harness_auth, and every place a Bearer token is minted, forwarded, or
validated. Duties: (1) keep tests/test_auth.py ahead of the implementation —
every auth behavior gets its negative test before the passing code exists;
(2) verify every service calls verify_token itself; (3) verify iss, aud, exp,
and signature are all checked and failures return 401 with an audit event;
(4) verify tokens never appear in logs or audit detail fields; (5) verify
system prompts are static constants (cache discipline). Report findings as a
checklist with file:line references. You may write tests; you may not weaken
any check to make a test pass. Flag anything you cannot verify for HUMAN REVIEW —
the human reads every token-touching line regardless.
```

### .claude/agents/service-builder.md
```markdown
---
name: service-builder
description: Builds one service at a time from SPEC.md. Use for scaffolding and implementing services/, apps/, and compose wiring.
---
You implement exactly one service per invocation, from its SPEC.md section.
Read the section, restate the contract (endpoints, ports, env, payloads) in
five lines, then build. Follow CLAUDE.md hard rules. Prefer the framework's
plainest idiom; no abstractions serving fewer than two callers. Wire the
service into docker-compose.yml with a healthcheck. Finish by running the
stack and demonstrating the service's exit criterion with a curl, then stop.
```

### .claude/agents/demo-verifier.md
```markdown
---
name: demo-verifier
description: Runs the demo script end to end against the live stack and reports divergences. Use at the end of each session.
---
Execute SPEC.md §7 against the running stack using curl (mint tokens from
identity-stub for dana, kim, pat). For each step record: request, expected
per spec, actual, PASS/FAIL. Verify audit rows exist for every step including
refusals and the bypass. Check answer quality: citations present, refusal
wording matches spec where the spec fixes it. Change nothing; produce a
numbered report. If seed data makes an answer mushy (e.g., no clearly
struggling advisees), say so and propose the seed adjustment.
```

(Data seeding doesn't need its own agent — service-builder handles `seed.py` from §5.)

## 10. Env and secrets

`.env.example`: `DEEPSEEK_API_KEY=`, `DEEPSEEK_BASE_URL=https://api.deepseek.com`, `ROUTER_MODEL=deepseek-v4-flash`, `AGENT_MODEL=deepseek-v4-pro`, `AGENT_THINKING=false`, `TUNNEL_TOKEN=` (optional), `JWT_AUDIENCE=harness-poc`. Compose injects into services that need them; UIs get no model keys (they never call models — that's the multiplexing claim). `.env` and `data/` gitignored.

## 11. Known honest shortcuts (say these in the demo, don't hide them)

Token pass-through instead of on-behalf-of exchange (production swaps the stub for Entra; enforcement code unchanged). Per-request MCP client construction (fine at demo scale). Fail-open router on parse failure (safe *because* enforcement is below — that's the argument). Client-held chat history. No suppression, no writes, no TLS between containers.
