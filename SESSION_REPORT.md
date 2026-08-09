# SESSION_REPORT — harness-poc Session 2

**Status: COMPLETE.** All eight acceptance criteria met. Written 2026-08-08,
branch `main`, HEAD `825f11f`, working tree uncommitted.

Session 2 of SPEC.md §8: four MCP servers with per-request validation and
tool-level authorization, the orchestrator, the gateway's router, the bypass
script, and the demo verification.

Companion documents: `DEMO_VERIFICATION.md` (the demo-verifier's own report,
left as written, with an addendum pointing here) and the approved plan at
`~/.claude/plans/read-claude-md-spec-md-in-velvety-sundae.md`.

---

## 1. Acceptance status per criterion

| # | Criterion | Status | Evidence |
|---|---|---|---|
| A1 | `uv run pytest tests/ -q` green including the new tests | **PASS** | `83 passed in 24.83s`. Was 72 collected with 15 deselected at session start; `addopts = "-m 'not session2'"` removed, so all now run by default. |
| A2 | `scripts/demo_bypass.sh` shows the MCP-level refusal | **PASS** | `Error executing tool get_my_advisees: get_my_advisees requires the advisor role.` / `isError: True` |
| A3 | The bypass lands an amber row in the audit viewer | **PASS** | `mcp-colleague tool_call refused get_my_advisees`. `services/audit/viewer.html:103` classes any `detail.decision === "refused"` as amber. No change to the audit service. |
| A4 | demo-verifier report exists, answers 1–7 attempted | **PASS** | `DEMO_VERIFICATION.md`, 960 lines, steps 1–8 plus cache and audit checks. |
| A5 | Every model-facing system prompt is a static constant | **PASS** | AST-parsed: `SYSTEM_PROMPT` and `ROUTER_PROMPT` are each a single plain string `Constant`. No f-string, `.format()`, or concatenation. |
| A6 | `git diff --stat` confined to the amended whitelist | **PASS** | See §5. `libs/harness_auth`, `services/identity-stub`, `services/audit` all clean. |
| A7 | `kill -STOP` a worker → unhealthy within ~30s | **PASS** | `SIGSTOP` to the uvicorn worker in mcp-kuali: healthy at t+20s, **unhealthy at t+30s**, healthy again after `SIGCONT`. |
| A8 | Second identical question reports nonzero cache hits | **PASS** | Zero of 48 model calls reported zero hits. Orchestrator `hit 3712 / miss 170` on repeats; router `hit 640` or `768` on every call, including a never-before-asked question. |

---

## 2. What was built

**`libs/harness_models`** (new shared package, whitelist amended by agreement).
The only place model clients or model config exist. Owns `DEEPSEEK_*` and
`AGENT_THINKING`, `router_model()`, `agent_model()`, and `UsageStats`. Added as
an editable path dependency by gateway and orchestrator only, so no model SDK
reaches the four MCP server images.

**`services/mcp-colleague`** — FastMCP over streamable HTTP, six tools per SPEC
§4.4, Starlette ASGI middleware calling `harness_auth.verify_token` on every
request before any tool dispatch.

**`services/mcp-labor`, `mcp-kuali`, `mcp-canvas`** — stamped from that
skeleton; differ only in tools, rules, database and port.

**`services/orchestrator`** — FastAPI :8010. Independent `verify_token`,
registry filtering before the agent is constructed, per-request MCP clients
carrying the caller's bearer, static system prompt, `tool_call` and
`answer_returned` audit rows.

**`services/gateway`** — router on `ROUTER_MODEL` with a strict-JSON schema,
retry-once-then-fail-open, `refused_at_gate` for a well-formed not-authorized
verdict. Echo mode removed. The triage-nurse comment is preserved verbatim at
`services/gateway/app.py:135`.

**`scripts/demo_bypass.sh`** — four acts: mint pat's token, skip the gate (hits
registry filtering), skip the orchestrator too (hits the tool-level refusal),
show both on the audit page.

---

## 3. Two defects found and fixed that would have shipped silently

### 3.1 A ContextVar would have let one caller act as another

The natural way to hand validated claims to a tool is a `ContextVar` set in
request middleware. **In FastMCP's default stateful mode this is wrong, and
wrong in the direction that matters.** Stateful sessions run every tool in the
task created by the *initialize* request, so a `ContextVar` set on a later
request is invisible and the tool keeps reading the identity of whoever opened
the session.

Measured, not inferred. A probe server opened a session with `Bearer FIRST` and
called a tool with `Bearer SECOND`; the tool read `FIRST`. The ASGI scope showed
`SECOND` correctly.

Fix: `stateless_http=True` on all four servers, and claims read from the
per-request ASGI scope (`services/mcp-*/mcp_auth.py`). The auth-reviewer
reproduced the attack independently against the running stack — a session opened
with dana's token and driven with kim's returns kim's refusal, and the server
emits no `mcp-session-id` at all — and added two regression tests
(`tests/test_auth.py:1082`, `:1109`) asserting observable behaviour, so they
hold whichever mechanism is in place.

### 3.2 An authorization refusal was being framed to the model as "try again"

`MCPToolset`'s `tool_error_behavior` defaults to `'retry'`, which converts a
tool error into a `ModelRetry` — literally instructing the model to self-correct
and try again. For an authorization refusal that is the opposite of SPEC §4.3's
*relay the refusal, never work around it*, and it consumes the run's retry
budget until the run raises, turning a correct refusal into a 500.

Set to `'failed'`, which shows the model the refusal as a result. Re-verified:
noor asking about `BUS-201-A` now produces one tool call and a relayed refusal
quoting the spec sentence verbatim.

---

## 4. Findings from the two agents, and what I did about each

### From the auth-reviewer

| Finding | Action |
|---|---|
| `iss` was tested only at the gateway; the orchestrator and four MCP servers were trusted on that one claim | **Fixed** — five new tests added |
| Three Session-1 tests asserted ECHO-mode behaviour | **Fixed** — rewritten to assert Session-2 behaviour. One relaxation only (`tools_used == []` → "is a list"), which was an echo artifact; the shape stays contractual |
| Orchestrator had no failure audit path — any exception was a 500 with no row | **Fixed** — `answer_failed` audit row and a 502 with a courteous message (`services/orchestrator/app.py`) |
| Gateway's relayed 401 wrote no gateway row | **Fixed** — `auth_failed` row before the raise |
| Refusal reasons record raw student ids while `args_hash` exists to avoid that | **Fixed the comment, kept the data.** An audit trail recording which record was asked about is the FERPA story, not a leak. What was wrong is that the code argued both ways; `_args_hash`'s docstring now says what it actually buys (a correlation key for arbitrary payloads) |
| `alg:none` and HS256-confusion still tested only at the gateway | **Not done, recorded.** `ALGORITHMS` is a shared module constant; the reviewer judged the coverage not worth the file growth. Noted so the decision is visible |

### From the demo-verifier

| Finding | Action |
|---|---|
| **Step 7 FAIL** — the qualification synthesis never called `get_course_outcomes`; it read answers off the program-occupation crosswalk, so there was no skills join at all | **Fixed and re-verified.** Two docstrings were misleading the model: the crosswalk read like a verdict, and the outcomes tool never said its skill tags share a vocabulary with occupation skills. Both rewritten, plus a fifth ground rule in the static system prompt. Now calls `get_course_outcomes` and reports Information Security Analysts **8/8**, Cloud Infrastructure Architects **2/7**, Data Scientists **0/7** — the strong / partial / miss the spec asks for |
| **Step 8 PARTIAL** — the two unmapped fast-growers surfaced, but adjacency was drawn occupation-to-occupation rather than from curriculum | **Fixed by the same change.** Now reports "AI/ML Engineers … 6/7 skills covered. Missing: **deep learning**" from actual program outcomes |
| **Step 6 FAIL on answer quality** — every "next term option" was a course the student was already sitting in | **Fixed — this was a real bug in my tool.** `requirement_progress` knew only *completed*, so in-progress courses reappeared as next-term options for all 300 students. Now three states, and `prereqs_satisfied` still counts only completed courses (a prerequisite in progress is not met). Re-verified: CYB-410/CYB-420 correctly reported as in progress, CYB-460 correctly blocked by them |
| Seed data: neither the designated partial-match nor the miss is fast-growing (3.1%, 8.2%), so the demo question's own filter excludes them | **Not done — Session 3.** SPEC §8 puts seed tuning in Session 3, and it is the user's call. The verifier's proposal (raise Network and Computer Systems Administrators from 3.1 to 21.5) is recorded in `DEMO_VERIFICATION.md` |
| One request in ~16 died on an MCP handshake timeout; per-request clients mean one slow server can kill a request needing none of its tools | **Partly addressed.** The failure now leaves an audit row and returns 502 rather than a silent 500. The underlying per-request construction is explicitly accepted by SPEC §11. Flagged below |
| Three audit rows lost when the audit service hot-reloaded mid-run | **No action — correct behaviour.** Fire-and-forget by design; the debounced warning did its job. This is what CLAUDE.md's pre-demo check exists for |

---

## 5. Deviations from the brief

| Brief said | Delivered | Why |
|---|---|---|
| Healthchecks `curl -sf`, 3s timeout | `python -c urllib.request.urlopen(..., timeout=3)` in `docker-compose.yml` only | No curl or wget in any image (`which curl wget` exits 1). curl would mean editing the off-limits identity-stub and audit Dockerfiles. **User approved.** Acceptance criterion unchanged and met |
| SPEC §1 "MCP SDK latest stable" | `mcp>=1.29,<2` (resolves to 1.29.0) | Latest stable 2.0.0 removed the FastMCP API SPEC §4.4 is written against. **User decision**, recorded as a SPEC §1 amendment by the user at `SPEC.md:35` |
| Extract shared middleware into `libs/harness_auth` if <40 lines | Duplicated across four servers, byte-identical (`md5 240a12306570689a51ed47edc554ab99`) | `libs/harness_auth` is fixed and untouchable per the brief's own rule. The duplication comment carries the safety condition per the user's clarification: it is safe **because, and only because,** the negative-auth tests are parametrized across all four servers |
| Diff confined to seven paths | Also `libs/harness_models/` and root `pyproject.toml` | `harness_models` per user decision. `pyproject.toml` because `addopts` deselected the very tests A1 requires |
| — | `DEMO_VERIFICATION.md`, `SESSION_REPORT.md` at repo root | Deliverables required by the brief and by CLAUDE.md |

**Files touched:** `docker-compose.yml`, `pyproject.toml`, `tests/{conftest,test_auth}.py`,
`services/gateway/{app,prompts,pyproject,Dockerfile,uv.lock}`, and new
`libs/harness_models/`, `services/orchestrator/`, `services/mcp-{colleague,canvas,kuali,labor}/`,
`scripts/demo_bypass.sh`.
`CLAUDE.md` and `SPEC.md` carry the user's own edits, not mine.
**Untouched and verified clean:** `libs/harness_auth/`, `services/identity-stub/`, `services/audit/`.

---

## 6. The thinking-mode trade-off — resolved

Multi-step syntheses (steps 7 and 8) narrate their working in the visible answer
— *"Now I have the CYB-BS skills. Let me match them against each occupation."*
Steps 1–5 never do this.

The cause is not a prompt defect. It is `AGENT_THINKING=false`, which SPEC §1
mandates for demo latency: with thinking disabled the model has nowhere to
reason except the answer.

| `AGENT_THINKING` | Step 7 answer | Latency |
|---|---|---|
| `false` (spec default, current) | Shows the skill-by-skill matching, then the verdict | ~15-20s |
| `true` | Leads straight with "Full match — Information Security Analysts 8/8 [kuali]" | ~33s |

Both produce the same correct analysis.

### RESOLVED — keep `AGENT_THINKING=false`

The visible method narration on multi-step syntheses is **a demo feature, not a
defect**: a grounded synthesis showing its joins is the claim the demo is making.
Watching the model list the fifteen CYB-BS skill tags and tick them off against
an occupation's skills is the difference between the room believing the join is
real and taking it on faith — which is exactly what SPEC §5's shared controlled
vocabulary exists to make provable. It also costs half the latency.

**Action taken:** the style rule I had added attempting to forbid narration has
been **removed** from `services/orchestrator/prompts.py`. It was ineffective
(verified — narration persisted with it in place) and it now contradicts intent.
The system prompt is otherwise unchanged and remains a single plain string
constant, AST-verified after the edit. No other change; the flag stays at the
spec default.

---

## 7. Open items, each with its disposition

Recorded here so this report stays the standalone source of truth. Items 1 and 2
are carried into Session 3 with the fixes already agreed; the rest are closed.

1. **Seed tuning — DEFERRED to Session 3, as its opening step. Both fixes
   pre-approved.**

   **(a) Growth rates.** Adopt the verifier's proposal so the designated
   partial-match and miss survive the demo question's own "fast-growing" filter.
   Today neither does (3.1% and 8.2%), so step 7's question excludes the very
   occupations that were tuned to demonstrate a partial and a miss. The
   verifier's specific proposal — raise Network and Computer Systems
   Administrators from 3.1 to 21.5 — gives step 7 an exact strong/partial/miss
   trio without disturbing step 8's two unmapped fast-growers. Full reasoning in
   `DEMO_VERIFICATION.md`.

   **(b) Recast demo step 6 rather than re-tuning S-1042.** Do **not** adjust
   S-1042's data. He is legitimately near the end of his program, and the answer
   he now produces is correct — "nothing to register for next term, CYB-460 is
   blocked until CYB-410 and CYB-420 finish". Bending a student's record to fit
   a slide would be the one dishonest thing in a demo whose entire argument is
   that the answers are real. Instead, cast a different, mid-program student for
   the beat: roughly three clean next-term options and exactly one
   prereq-blocked course. Record the chosen student id in
   `DEMO_VERIFICATION.md` so the demo script and the verifier agree on who is
   being asked about.

2. **MCP handshake failures (~1 in 16 requests) — FIX in Session 3, two parts.**
   Per-request client construction stays, per SPEC §11.

   **(a) Build clients only for servers the caller can actually reach.** Today
   the orchestrator opens connections to all four servers regardless of the
   filtered tool set, so one slow server can fail a request that needed none of
   its tools. Construct a client only when at least one tool from that server
   survives registry filtering. **pat's requests must never open a connection to
   mcp-colleague at all.** This is least exposure first and a smaller failure
   surface second: a connection that is never opened cannot fail, and cannot be
   the subject of an argument about what it might have returned.

   **(b) Retry a failed connect/handshake once** with a short backoff before
   returning the audited 502. The one observed failure succeeded immediately on
   retry, so a single attempt is leaving an easy win on the table.

   **Verifier check to add:** 20 consecutive gateway requests with zero
   handshake failures.

3. **`alg:none` and HS256-confusion tested only at the gateway — ACCEPTED as
   recorded, no action.** Mitigated by `ALGORITHMS` being one shared module
   constant across all six services. Recorded rather than hidden.

4. **Non-`http` scopes bypassing the auth middleware — SUPERSEDED: CLOSED IN CODE.**
   The middleware previously passed every non-`http` scope to the application so
   that `lifespan` could reach the session manager, which meant any future scope
   type — websocket included — would have been handed to the app with no token
   checked. Not exploitable at the time (zero `WebSocketRoute`s existed), but a
   trapdoor for whoever added one.

   **Mechanism.** `BearerAuthMiddleware.__call__` is now an allowlist rather
   than a denylist. `lifespan` passes through; `GET /healthz` passes through;
   `http` is validated as before; **everything else is closed by
   `_close_unauthenticated` without ever calling the app**, so no route matches
   and no tool code runs. A websocket has its `websocket.connect` consumed and
   is answered with `websocket.close` code 1008 (policy violation) *before*
   `accept`, so the upgrade never completes and nothing is echoed back. Any
   other scope type is dropped with no reply at all. Every refusal writes an
   `auth_failed` audit row naming the connection type.

   **Verified.** All four copies remain byte-identical
   (`md5 937c7753d32da38d1f44f5c505ab3d51`). A raw hand-framed upgrade against
   each server returns `HTTP/1.1 403 Forbidden` — uvicorn's rendering of a
   close-before-accept — never 101.

   **Regression test:** `test_websocket_upgrade_is_refused_without_reaching_the_server`,
   parametrized across all four servers, carrying a **valid** token so the
   refusal must come from the connection type rather than from authentication.

   One thing worth recording about that test. The obvious assertion — "status is
   not 101" — is **worthless here**, and I confirmed it empirically rather than
   assuming: Starlette also closes a websocket matching no route, and uvicorn
   reports both closes as 403, so a status-only test passes against the very
   trapdoor it is meant to guard. I reverted the middleware and watched it stay
   green. The test therefore asserts the **audit row**, which only the
   middleware can write and only if it handled the connection itself. Re-checked
   both ways: green with the fix, and failing on exactly the reverted server
   with the other three still passing.
5. **The duplication safety condition — STANDING constraint, no action.** The
   four byte-identical `mcp_auth.py` copies are safe only while the negative-auth
   tests stay parametrized across all four servers. If that parametrization is
   ever narrowed, the decision to duplicate must be revisited. This is a
   permanent condition on future sessions, not an open item to close.

6. **DeepSeek thinking-mode docs contradict themselves — ACCEPTED, no action.**
   The API reference nests `reasoning_effort` inside a top-level `thinking`
   object; the Thinking Mode guide shows a top-level form, with a literal Python
   syntax error in all three of its examples. I used the nested form from the
   formal request schema and verified it empirically rather than trusting either
   page: on the same prompt, `thinking: disabled` returns no reasoning tokens
   (1 completion token) and `enabled` returns 47. The explanatory comment in
   `libs/harness_models/factory.py` stays, since the next reader will hit the
   same contradiction.

---

## 8. Disposition summary

| Item | Disposition | Carried to Session 3 |
|---|---|---|
| §6 `AGENT_THINKING` flag | **RESOLVED** — stays `false`; narration reclassified as a demo feature; the ineffective style rule removed from the system prompt | No |
| §7.1 Seed tuning | **DEFERRED** — Session 3 opening step, both fixes pre-approved | Yes — (a) growth rates, (b) recast step 6's student |
| §7.2 Handshake failures | **FIX** — build clients only for reachable servers; retry once with backoff | Yes — plus a 20-request verifier check |
| §7.3 `alg` coverage at gateway only | **ACCEPTED** as recorded | No |
| §7.4 Websocket / non-`http` scopes | **SUPERSEDED** — closed in code, regression-tested | No |
| §7.5 Duplication condition | **STANDING** constraint | Permanent |
| §7.6 DeepSeek docs contradiction | **ACCEPTED** — nested form verified empirically | No |

---

## 9. Commands run, for reproduction

```bash
docker compose up -d --build          # 8 services, all healthy
uv run scripts/seed.py                # already seeded at session start
uv run pytest tests/ -q               # 83 passed in 24.83s
./scripts/demo_bypass.sh              # both layers refuse; amber row lands

# healthcheck acceptance
docker compose exec -T mcp-kuali python -c "import os,signal; os.kill(8, signal.SIGSTOP)"
sleep 30 && docker compose ps         # mcp-kuali unhealthy
docker compose exec -T mcp-kuali python -c "import os,signal; os.kill(8, signal.SIGCONT)"

# cache discipline
curl -s 'http://localhost:8030/events?limit=40' | grep answer_returned

# scope
git status --short libs/harness_auth services/identity-stub services/audit   # clean
```
