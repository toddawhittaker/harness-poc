# Demo verification — SPEC §7 against the live stack

## Demo casting — who the script asks about

Recorded here so the demo script, the seed guards, and the verifier all name the
same people. Set in Session 3.

| Demo moment | Persona asking | Subject | Why this one |
|---|---|---|---|
| 6 — record vs pulse | dana | **S-1055, Leon Cline (CS-BS)** | Mid-program: 9 of 24 credits, taking CS-210 now. Next term offers exactly three courses he can take (CS-310, CS-350, CS-410 — all with seats) and exactly one he cannot (CS-460 Capstone, needs CS-310 and CS-350 first). GPA 3.41, logged in 3 days ago, so nothing distracts from the question. |
| — | — | S-1042, Nathan Osborne | **No longer used by step 6, and deliberately unchanged.** He is near the end of CYB-BS, so his honest answer is "nothing new to register for until CYB-410 and CYB-420 finish". `scripts/seed.py::verify` asserts he still has zero open options, so nobody can quietly retune him into a slide. |
| 1 | dana | her 25 advisees, 8 quiet | unchanged |
| 5 | noor, then kim | CYB-310-A, then BUS-201-A (refused), then the rollup | unchanged |

`STEP_6_STUDENT` in `scripts/seed.py` is the single source of that id; `verify()`
fails the seed run if the shape above stops being true.

---

# Session 3 verification — the current record

Run 2026-08-09 02:33:51–02:43:27 UTC by the demo-verifier agent, against the
live compose stack with all ten services healthy. Nothing in the repository was
changed. Steps 1, 2, 3, 5, 6, 7 and 8 were driven through the real Chainlit apps
over socket.io with a real `POST /login`, which is what the demo does; step 4 ran
`./scripts/demo_bypass.sh` unmodified. Audit rows 1747–1941 belong to this run —
195 rows, 76 of them from the ten-step script.

## Summary

| # | SPEC §7 claim | Result | Change since Session 2 |
|---|---|---|---|
| 1 | Dana: struggling advisees, quiet ones flagged, `[colleague]` | PASS | unchanged |
| 2 | Kim, same question: aggregates, no individual names | PASS on the claim; the answer reads badly on a projector | worse |
| 3 | Pat: courteous gate refusal, then a labor answer | PASS | old wording wart gone, a new one appeared |
| 4 | The bypass, blocked at the MCP layer | PASS | now also proves the connection is never opened |
| 5 | Noor's section, Noor refused by name, Kim's rollup | PASS | unchanged |
| 6 | Dana: what should S-1055 take next term | **PASS — was FAIL** | fixed |
| 7 | Qualification synthesis: strong, partial, miss | **PASS — was FAIL** | fixed |
| 8 | Gap synthesis: the two unmapped fast-growers | **PASS — was PARTIAL** | fixed |
| 9 | Audit page shows the session, refusals and bypass included | PASS | unchanged |
| 10 | Honesty slide claims | PASS (one claim untestable) | unchanged |
| A | Prompt-cache discipline (SPEC §1) | PASS — 59 model calls, 0 with zero cache hits | unchanged |
| B | 20 consecutive gateway requests, zero handshake failures | PASS — 20/20, 0 retries | fixed |
| C | Registry filtering visible in the audit trail | PASS | new evidence |
| D | Two apps visibly distinct; `tools:` suffix subtle | PASS | new |
| E | Answers that land badly in a room | **One real problem: model narration** | worse |

## The three steps that were broken, and why they now pass

**Step 6 — was FAIL on answer quality, now PASS.** Demo moment 6 asks dana what
S-1055 should take next term. The answer names Leon Cline, 3.41 GPA, 9 of 24
credits, currently taking CS-210, then three offered courses with seat counts
(CS-310 with 36 seats, CS-350 with 21, CS-410 with 35) and exactly one blocked:
"CS-460 (Capstone) remains locked until both CS-310 and CS-350 are completed
[colleague]." CS-210 — the course he is sitting in — does not appear among the
options. The verifier confirmed that is structural rather than lucky:
`services/mcp-colleague/app.py` skips in-progress courses and reports them
separately, so the Session 2 defect is fixed for all 300 students, not only for
the cast one. Audit rows 1787–1795, three `tool_call` rows all `decision: ok`.

**Step 7 — was FAIL, now PASS.** The qualification question now performs the
exact-string skill join the spec describes, and the trio survives the question's
own "fast-growing" filter: Information Security Analysts at 32.7% growth is a
strong match at 8 of 8 skills; Network and Computer Systems Administrators at
21.5% is the partial at 3 of 6 (missing cloud architecture, containerization and
infrastructure automation); AI/ML Engineers at 35.2% is the clean miss at 0 of 7.
`[kuali]` and `[labor]` interleave throughout. Raising Network and Computer
Systems Administrators from 3.1% to 21.5% is what put the partial match inside
the band the question asks about. Audit rows 1796–1805.

**Step 8 — was PARTIAL, now PASS.** Both unmapped fast-growers surface with
adjacency drawn from real curriculum: AI/ML Engineers at 35.2% with 4 of 7 skills
covered by DAT-MS and CS-BS and deep learning missing from the whole catalog;
Cloud Infrastructure Architects at 33.8% with 4 of 7 covered by IS-MS and CS-BS
and containerization plus infrastructure automation missing. The verifier checked
all three "missing anywhere" claims directly against `data/kuali.db` and they are
true. Seventeen audit rows (1806–1822), nine tool calls across two servers in a
single turn — the best evidence in the script that a real agent loop is running.

## Checks A to D, in brief

**A. Prompt-cache discipline: PASS, decisively.** Fifty-nine model calls across
the script and the 20-request run, and not one reported zero cache hits. The
router's hit count was 768 on every single call, with misses between 14 and 27 —
the signature of a genuinely fixed prefix where only the short dynamic tail
changes. Orchestrator hits scale with role, from 896 for pat with two tools in
view to 6016 for kim with ten, which is what happens when tool schemas sit inside
a cacheable prefix. Residual orchestrator misses are the tool result, which is
new content on every run by definition and should never cache.

**B. Twenty consecutive gateway requests: PASS, 20 of 20.** Zero request
failures, zero `answer_failed` rows, zero handshake retries, latencies between
8.3 and 14.6 seconds. Session 2's roughly one-in-sixteen handshake failure rate
is gone. Worth noting which half of the fix did the work: the `reconnected` field
is empty on all twenty, so the retry never fired. Not building clients to servers
the caller cannot use is what fixed it; the retry is insurance.

**C. Registry filtering, visible in the trail: PASS.** Every orchestrator answer
now records which servers it reached. Pat's two requests both carry
`servers: ["labor"]`; noor's both carry `servers: ["canvas", "kuali", "labor"]`.
Neither reaches the student record system. The container logs prove the stronger
claim — that no connection was opened at all. Across pat's step 3 window
(02:35:00–02:35:10) mcp-colleague logged nothing while mcp-labor logged its
handshake and tool call; the single mcp-colleague line in that period comes from
`172.20.0.1`, the host, which is the bypass script's own curl, not from
`172.20.0.8`, the orchestrator.

**D. The two apps, and the receipts line: PASS.** They differ before anyone types
anything: `GET /auth/config` returns `"default_theme": "light"` on the advisor
app and `"dark"` on the executive one. The palettes are not near-misses — warm
hues 20 to 36 against cool hues 205 to 222, burnt orange on cream against bright
blue on near-black — and even the corner radius differs. Everything that is not
theme is identical: the two `harness_chat.py` files are byte-identical and `diff`
on the two `app.py` files returns only the docstring, the name, the greeting and
the starters. The `tools: …` suffix renders as a muted 0.8125rem footnote at 85%
opacity, and an empty tool list renders as `no tools called` rather than being
hidden — which is the whole story in step 3a and step 4.

## Findings, all of them outside Session 3's permitted diff

None of these were acted on. Each names the file and the change.

1. **Model narration before the answer — the one that matters.** In steps 2, 7
   and 8 the model narrates its own working first. Steps 7 and 8 get a line or
   two, which is survivable. Step 2 gets 130 words of first-person deliberation
   with a visible false start ("Wait — I have no tool that maps an advisor name
   to their advisees. Let me check if there's anything I missed"), which is about
   a third of the answer, on the slide where the room decides whether this is a
   product or a chatbot demo. The system prompt already says "Lead with the
   answer"; the model is disobeying an instruction that exists. Fix:
   `services/orchestrator/prompts.py`, a rule forbidding first-person process
   narration. It is inside the static prefix, so cache discipline is unaffected.
2. **`SPEC.md` §7 step 6 still says S-1042.** The recast to S-1055 was
   pre-approved in `reports/session-2.md` §7.1(b) and both Chainlit starter
   buttons already say S-1055, but the master document does not. CLAUDE.md says
   the spec wins where code and spec conflict, so this is a trap for the next
   reader. One id.
3. **The gate tells pat that deans get advisee detail.** mcp-colleague's own
   spec-fixed string says the opposite: "Individual student records require an
   advisor assignment; deans receive aggregates." Two screens in the same demo
   contradict each other. Fix: `services/gateway/prompts.py`, have the
   `advisee_detail` bullet name advisors only.
4. **A bad tool argument is audited as a refusal.** `services/mcp-kuali/rules.py`
   catches every non-`ToolError` exception and writes `decision: "refused"` with
   the exception class name, and the viewer paints any refused row amber. Row
   1797 is therefore an amber "mcp-kuali refused the dean" whose honest
   explanation is "the model typed a program code that does not exist", sitting
   beside three amber rows that are genuine RBAC refusals. Fix: give bad input
   its own decision value and its own colour, so refusals mean refusals.
5. **The audit viewer fetches only the newest 100 events.** The ten-step script
   writes 76 rows, so step 1 survives with 24 rows of headroom. Two warm-up
   questions before the demo, or one extra Q&A exchange mid-script, push step 1
   off the page at the moment you scroll back to it. `services/audit/viewer.html`,
   `limit=100` to `limit=200`.
6. **The pre-demo check in CLAUDE.md is weaker than it looks.** It reads only the
   `audit` and `gateway` logs, but three of the eleven dropped events found
   during Session 3 came from mcp-kuali, mcp-labor and mcp-colleague — the
   tool-call rows the demo actually points at. And `tail -20` covers roughly 100
   seconds, so a drop from three minutes ago is already out of the window. A
   replacement that answers the question, with no code change:
   `docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"`.
   For the record: zero events were dropped at or after 02:33:00, so this run's
   receipts are complete and step 9 is safe.
7. **The dean answer still offers a route to per-student data.** Milder than
   Session 2 but not gone: "If you can provide section IDs for the sections your
   advisees are in, I can pull per-student engagement for those sections." Kim is
   a dean, so that really would work. Not an authorization failure; it just reads
   badly in the beat about roles gating data. Extend the orchestrator prompt's
   rule 3 to cover offering a workaround, not only attempting one.
8. **Step 8 asserts about six programs from four tool calls.** The claims happen
   to be true — verified against `data/kuali.db` — but `get_course_outcomes` was
   called four times and there are six programs. If someone asks "did you check
   HIM-BS?", the honest answer is "it did not look".
9. **Seed, minor: BUS-201-B holds three students.** SPEC §5 asks for it to be
   visibly unhealthy, and it is, but on an n of three. The script never shows it
   — step 5b shows only the refusal — so this matters only in Q&A. Raise its
   enrollment to eight or ten if anyone is in `scripts/seed.py` anyway.
10. **Seed, cosmetic: repeated surnames.** Five students are surnamed Whitfield
    like the advisor persona, but none is one of dana's advisees and none is in
    CYB-310-A, so no Whitfield student appears anywhere in the script as it now
    runs. Duplicate surnames persist inside dana's list. Dropping "Whitfield"
    from `LAST_NAMES` closes it; not worth opening the file for.

Full run transcripts, one file per step, are in the session scratchpad and are
quoted at length in `SESSION_REPORT.md`.

---

# Session 2 verification — superseded, kept for its reasoning

Everything below is the Session 2 verifier's report, left exactly as written. It
is retained because `reports/session-2.md` cross-references its analysis, in
particular the growth-rate proposal that Session 3 acted on. Its findings on
steps 6, 7 and 8 are closed; see the Session 3 record above.

> **Addendum added after this report was written (not by the verifier).**
> Steps 6, 7 and 8 were fixed in response to the findings below and re-verified.
> Step 7 now performs the exact-string skill join and reports 8/8 for
> Information Security Analysts; step 8 now draws adjacency from curriculum
> ("6/7 covered, missing deep learning"); step 6 no longer offers courses the
> student is currently taking. The seed-data findings at the end of this report
> still stand and were NOT acted on — they are Session 3 tuning work. See
> `reports/session-2.md` for what changed and the re-verification evidence.
> The body of this report is left exactly as the verifier wrote it.

Run at 2026-08-09 01:07–01:16 UTC, end of Session 2, by the demo-verifier agent.
Nothing in the repository was changed. Every result below comes from `curl`
against the running compose stack.

The two Chainlit UIs are Session 3 work and do not exist yet, so every step that
the script performs in a UI was driven against the gateway's HTTP API instead —
`POST http://localhost:8000/chat`, which is exactly what the UIs will call.
Step 4 is the deliberate exception: it calls the orchestrator and mcp-colleague
directly, which is the point of that step.

## Summary

| # | SPEC §7 claim | Result |
|---|---|---|
| 1 | Dana: struggling advisees — her 25, quiet ones flagged, `[colleague]` | **PASS** |
| 2 | Kim, same question — program aggregates, no individual names | **PASS** (one wording wart) |
| 3 | Pat: courteous gate refusal, then a labor question answered | **PASS** (one wording wart) |
| 4 | The bypass — registry filtering, then the mcp-colleague refusal | **PASS** |
| 5 | Noor's section, Noor refused by name, Kim's rollup | **PASS** |
| 6 | Dana: what should S-1042 take next term | **PASS on mechanism, FAIL on answer quality** |
| 7 | Qualification synthesis — strong / partial / miss from skills | **FAIL** |
| 8 | Gap synthesis — the two unmapped fast-growers, adjacency noted | **PARTIAL PASS** |
| — | Prompt-cache discipline (SPEC §1) | **PASS** |
| — | Audit row present for every step, refusals and bypass included | **PASS** |
| — | Spec-fixed refusal strings verbatim (§4.4 ×2, §4.6) | **PASS** |

Two things need work before this is demo-ready: step 7 does not do the synthesis
the spec describes, and step 6's answer is confusing because of how the seed data
lines up. Both are described in full below with proposed fixes.

### A caveat about this run

Another session was working in this repository at the same time. It ran the
negative-auth test suite and edited files, which restarted the audit service at
01:13:13. Foreign audit rows appear in some of the ranges quoted below; where
that happens I say so and give the row IDs that belong to this run. One
consequence is discussed under "Observations" — it is worth reading, because it
is the failure mode `CLAUDE.md`'s pre-demo check exists to catch.

### How each step was driven

Every step used the same helper: mint a token, note the highest audit row ID,
POST to the gateway, then list the audit rows created since the mark.

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/token \
  -H 'content-type: application/json' \
  -d '{"persona":"dana","password":"demo"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"message":"Which of my advisees seem to be struggling this term?","history":[]}'

curl -s "http://localhost:8030/events?limit=100"
```

---

## 1. Dana — "Which of my advisees seem to be struggling this term?"

**Expected (SPEC §7.1):** her 25 advisees, the quiet ones flagged, cited
`[colleague]`.

**Request:** persona `dana`, gateway `/chat`, empty history.

**Actual reply (abridged; full text preserved in the run log):**

> ### ❗ Immediate concern
>
> **Leon Delgado (S-1035)** — BUS-BS, GPA 1.85, last login 13 days ago [colleague]
> - BUS-310: D at midterm
> - BUS-330: incomplete carried from prior term
> GPA is below 2.0 and hasn't logged in for nearly two weeks.
>
> **Krista Leblanc (S-1049)** — BUS-BS, GPA 1.94, last login 21 days ago [colleague]
> …
> **Zachary Hendricks (S-1054)** — IS-MS, GPA 2.08, last login 25 days ago [colleague]
> …
> ### ✅ Appear on track
>
> The remaining 14 advisees have no term grade flags, recent logins, and GPAs
> above 2.0.

`tools_used: ['get_my_advisees']`

**Assessment: PASS.** Eleven students named plus "the remaining 14" accounts for
exactly 25. All eight seeded quiet students (last login > 10 days) appear, and
they lead the list, ordered worst first. Every fact carries `[colleague]` and no
other marker, which is correct — only mcp-colleague was called. The answer has
real texture: GPA, days since login, and per-course grade flags.

**Audit rows (IDs 734–738), all present:**

```
  734  01:08:59  gateway        router_classified  dana   {"intent": "advisee_detail", "in_scope": true, "plausibly_authorized": true, "prompt_cache_hit_tokens": 768, "prompt_cache_miss_tokens": 20, ...}
  735  01:09:01  mcp-colleague  tool_call          dana   {"tool": "get_my_advisees", "args_hash": "44136fa355b3", "decision": "ok"}
  736  01:09:10  gateway        request_completed  dana   {"intent": "advisee_detail", "routed": true, "tools_used": ["get_my_advisees"], "latency_ms": 12200.0}
  737  01:09:10  orchestrator   tool_call          dana   {"tool": "get_my_advisees", "via": "orchestrator"}
  738  01:09:10  orchestrator   answer_returned    dana   {"tools_used": ["get_my_advisees"], "tools_offered": [...8 tools...], "latency_ms": 10834.7, ...}
```

The `tools_offered` field is worth pointing at during the demo: dana's registry
allowlist is the eight advisor tools and nothing else.

---

## 2. Kim — the same question

**Expected (SPEC §7.2):** program aggregates, no individual student names, same
harness, same second.

**Request:** persona `kim`, identical message.

**Actual reply:**

> I have program-level data, but I don't have a tool that tells me which specific
> students are _your_ advisees. …
>
> **Programs with the highest share of quiet students (>10 days since login):**
> - Cybersecurity, BS (CYB-BS): 9.1% [colleague]
> - Information Systems, MS (IS-MS): 8.8% [colleague]
> - Health Information Management, BS (HIM-BS): 8.3% [colleague]
> - Business Administration, BS (BUS-BS): 8.3% [colleague]
> - Computer Science, BS (CS-BS): 8.2% [colleague]
> - Data Analytics, MS (DAT-MS): 2.3% [colleague]
>
> **This week's engagement trouble spots:**
> - BUS-BS: only 67.9% logged in this week, 34 missing submissions [canvas]
> - IS-MS: 27 missing submissions across just 2 sections [canvas]
>
> **What I can't do:** I have no tool that accepts an advisor name … Would you
> like me to drill into specific sections in any of these programs to identify
> struggling students there, and you can cross-reference with your advisee list
> manually?

`tools_used: ['get_program_summaries', 'get_program_engagement_rollup']`

**Assessment: PASS on the spec claim.** Zero individual student names. Aggregates
only. It also joined two sources unprompted and cited both correctly, which is a
bonus over what the spec asks for.

**Wart worth fixing before the demo.** The closing sentence offers to walk
section by section so Kim can "cross-reference with your advisee list manually."
Kim is a dean; `get_section_engagement` returns per-student rows to deans, so
that offer is a genuine route to reassembling individual student data from
aggregates. It is not an authorization failure — a dean is allowed to see section
rosters — but it reads badly in a room being told that roles gate data, and it
sits awkwardly beside the orchestrator prompt's own rule 3 ("Never work around a
refusal … by assembling it from aggregates"). Consider extending that rule to
cover offers as well as attempts.

**Audit rows (IDs 739–745), all present**, including one `tool_call` row from
each of mcp-canvas and mcp-colleague plus the orchestrator's mirrored pair.

---

## 3. Pat — refused, then answered

### 3a. The gate refusal

**Expected (SPEC §7.3):** courteous gate refusal.

**Actual reply, in full:**

> Advisee-level detail is held by advisors, faculty, and deans. As an adjunct you
> can reach labor-market and public curriculum data instead.

`tools_used: []`

**Assessment: PASS.** Courteous, one sentence of explanation, no apology spiral,
and it names what Pat *can* reach. It came back in 1.66 seconds because it never
left the gateway.

**Wart:** the refusal promises "public curriculum data", but `config/registry.yaml`
gives the adjunct role only `list_occupations` and `get_occupation`. There are no
curriculum tools in Pat's allowlist, so a follow-up curriculum question will
disappoint. The router prompt in `services/gateway/prompts.py` describes
categories but never tells the model what an adjunct actually holds, so the model
is guessing. Naming the two labor tools explicitly in the router prompt's
`labor_market` bullet would close it.

**Audit rows (IDs 746–747), both present:**

```
  746  01:09:47  gateway  refused_at_gate    pat  {"intent": "advisee_detail", "in_scope": true, "plausibly_authorized": false, "latency_ms": 1664.1}
  747  01:09:47  gateway  router_classified  pat  {"intent": "advisee_detail", "in_scope": true, "plausibly_authorized": false, ...}
```

Note there is no orchestrator row and no MCP row. The request never went past the
front door — which is exactly the contrast step 4 then destroys.

### 3b. "Which occupations are growing fastest?"

**Expected:** answered.

**Actual:** a full twelve-row table, correctly ordered by growth, ending:

> The top three — AI/ML Engineers, Cloud Infrastructure Architects, and
> Information Security Analysts — all show growth above 30% with median wages
> exceeding $120K. [labor]

`tools_used: ['list_occupations']`

**Assessment: PASS.** The numbers match `data/labor.db` exactly. The `[labor]`
marker appears once, at the end, rather than on each row; the spec asks for
citation, not for a marker per table cell, so this stands.

**Audit rows (IDs 748–752), all present**, including the mcp-labor `tool_call`
with `decision: ok`. `tools_offered` on row 752 is `["get_occupation",
"list_occupations"]` — the whole of Pat's world, visible in the receipt.

---

## 4. The bypass

**Expected (SPEC §7.4):** registry filtering at the orchestrator, then the
tool-level refusal from mcp-colleague, both landing in the audit view.

**Command:** `./scripts/demo_bypass.sh` (run unmodified).

**Actual output:**

```
==> 1. Mint a real token for pat (adjunct — no data roles)
    signed RS256, sub=pat  name=Pat Reyes  roles=['adjunct']

==> 2. Skip the gate. Curl the orchestrator directly.
    tools the model actually called: none

    I don't have access to a tool that can look up advisees by advisor name or
    faculty ID. … The tools I have available are for occupations and
    labor market data only. I can't answer this one.

==> 3. Skip the orchestrator too. Call the tool server itself.
    Error executing tool get_my_advisees: get_my_advisees requires the advisor role.
    isError: True

==> 4. Both attempts are on the record.
    01:10:17  orchestrator    answer_returned
    01:10:17  mcp-colleague   tool_call        refused   get_my_advisees
```

**Assessment: PASS, and this is the strongest step in the script.** Layer 2
behaved exactly as claimed — the model called nothing, because there was nothing
to call. Layer 3 refused on its own re-validation of Pat's token, with the
message SPEC §4.4 fixes.

**Audit rows (IDs 753–754), both present:**

```
  753  01:10:17  orchestrator   answer_returned  pat  {"tools_used": [], "tools_offered": ["get_occupation", "list_occupations"], "latency_ms": 2804.2, ...}
  754  01:10:17  mcp-colleague  tool_call        pat  {"tool": "get_my_advisees", "args_hash": "44136fa355b3", "decision": "refused", "reason": "get_my_advisees requires the advisor role."}
```

Row 753's `tools_used: []` next to `tools_offered: [two labor tools]` is the
registry-filtering claim in machine-readable form. Row 754 is the amber row.
There are no gateway rows for either attempt, because the gateway was skipped —
which is itself visible evidence in the audit table.

---

## 5. Faculty versus dean

### 5a. Noor — "How is my CYB-310 section doing this week?"

**Actual reply, in full:**

> **CYB-310-A** is in solid shape this week. All 8 students logged in (100%
> active) and only 2 missing submissions across the section [canvas].
>
> Two students need attention:
> - **Theresa Whitfield** — last login 2 days ago, 1 missing submission [canvas].
> - **Zachary Whitfield** — last login today, 1 missing submission [canvas].
>
> The other six — Brandon Sharma, Diana Pham, Sara Kaur, Derek Hoffman, Jacob
> Underwood, and Terrence Kaur — are all at 8 submitted, 0 missing, with recent
> logins [canvas].

`tools_used: ['get_my_sections', 'get_section_engagement']`

**Assessment: PASS.** Cited `[canvas]` throughout and nothing else, correctly.
The model resolved "my CYB-310 section" to `CYB-310-A` by calling
`get_my_sections` first, which is the right shape. Numbers match the seed
(8 students, mean 1.4 days since login, 2 missing).

**Audit rows: IDs 755–761, all present.**

### 5b. Noor — "And how's BUS-201-A doing?"

Sent with the prior turn in `history`, the way a UI would.

**Expected (SPEC §4.6):** refusal naming the section, verbatim: *"Section
BUS-201-A is not among your assigned sections; cross-section views belong to the
dean."*

**Actual reply:**

> I can't pull engagement for BUS-201-A — it isn't among your assigned sections.
> The system says cross-section views belong to the dean, so you'd need to ask
> them for that data [canvas].

**Assessment: PASS.** The tool layer produced the spec string exactly, and the
model relayed it without working around it. Audit row 799:

```
  799  01:10:53  mcp-canvas  tool_call  noor  {"tool": "get_section_engagement", "args_hash": "8dcd893de78e", "decision": "refused", "reason": "Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean."}
```

**Minor wart:** the model appended `[canvas]` to a sentence that is a refusal, not
a fact from Canvas. Harmless, slightly odd on a projector.

**Audit rows: IDs 797, 799, 801–803, all present.** (This range also contains
rows from the other session; the ones listed are this run's.)

### 5c. Kim — "How's engagement across all programs this week?"

**Actual reply:**

> | Program | Enrollment | % Logged In | Missing Submissions | Sections |
> |---|---|---|---|---|
> | **BUS-BS** | 28 | **67.9%** | 34 | 4 |
> | CS-BS | 20 | 75.0% | 8 | 3 |
> | IS-MS | 22 | 81.8% | 27 | 2 |
> | CYB-BS | 38 | 84.2% | 22 | 5 |
> | HIM-BS | 29 | 89.7% | 21 | 3 |
> | **DAT-MS** | 35 | 97.1% | 26 | 3 |
>
> **Needs attention:** BUS-BS is the clear concern …

`tools_used: ['get_program_engagement_rollup']`

**Assessment: PASS.** Six programs, the building rather than the room. Cited
`[canvas]`. The faculty/dean asymmetry the step exists to show lands cleanly
against 5b.

**Audit rows: IDs 841–845, all present.**

### Spec-fixed refusal strings, checked directly at the tool layer

Because registry filtering means a dean never even sees `get_student_summary`
through the orchestrator, the SPEC §4.4 dean line is not exercised by steps 1–8.
It was verified directly:

```bash
curl -s -X POST http://localhost:8021/mcp \
  -H "Authorization: Bearer $KIM_TOKEN" \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"get_student_summary","arguments":{"student_id":"S-1042"}}}'
```

| Check | Result |
|---|---|
| kim (dean) → `get_student_summary(S-1042)` | `Individual student records require an advisor assignment; deans receive aggregates.` — **verbatim** |
| dana → `get_student_summary(S-1044)` (not hers) | `Student S-1044 is not among your assigned advisees.` — **verbatim** |
| noor → `get_section_engagement(BUS-201-A)` | `Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean.` — **verbatim** |
| kim → `get_section_engagement(BUS-201-A)` | succeeds, returns the 4-student roster — the asymmetry holds |

All three spec-fixed strings match SPEC §4.4 and §4.6 character for character.

---

## 6. Dana — "What should S-1042 take next term?"

**Expected (SPEC §7.6):** degree progress, prereqs met, next-term offerings,
cited `[colleague]`.

**First: the seed-data question raised in the brief is settled.** S-1042 *is*
dana's advisee. The commit "Punch a hole in dana's advisee block" removed S-1044,
not S-1042, and the database on disk reflects it:

```
$ sqlite3 data/colleague.db "select * from advisor_assignments where student_id in ('S-1042','S-1044');"
dana|Dana Whitfield|S-1042
adv-003|Rebecca Lin|S-1044
```

No re-run with a different ID was needed.

**Actual reply (second of two runs, quoted in full because the wording matters):**

> Nathan Osborne is in the CYB-BS program with a 2.74 GPA, 15 of 24 credits
> completed, and last logged in 5 days ago [colleague].
>
> He's currently enrolled in CYB-410 and CYB-420, which completes all remaining
> non-capstone coursework [colleague]. There are no term grade flags right now.
>
> For next term (2027SP), only two courses are offered that he hasn't already
> completed:
> - **CYB-410** — Security Architecture (3 credits), 38 seats available
> - **CYB-420** — Governance, Risk, and Compliance (3 credits), 21 seats available
>
> **But there's a catch: he's already taking both of those right now this term.**
>
> The one course he hasn't taken — **CYB-460 (Cybersecurity Capstone)** — is
> blocked because it requires both CYB-410 and CYB-420 as prerequisites, which
> aren't yet complete [colleague].
>
> **The bottom line:** Assuming he passes both CYB-410 and CYB-420 this term, his
> only next-term option is CYB-460. … There's nothing else on the menu until
> those two are in the books.

`tools_used: ['get_student_summary', 'get_student_degree_progress', 'get_next_term_options']`

**Assessment: PASS on mechanism, FAIL on answer quality.**

The mechanism is perfect. Three mcp-colleague tools fired, all `decision: ok`,
in the right order. Degree progress, prereq state, and next-term offerings all
appear. The prereq block on CYB-460 is correct and interesting.

The answer is not usable on stage. Both "next term options" are the two courses
Nathan is sitting in right now, and the model — correctly, honestly — spends a
paragraph pointing that out. The demo beat is supposed to be "Colleague knows
what comes next"; what the room will hear is "the system suggests he take the
courses he is already taking." This reproduced identically across both runs, so
it is data, not model variance. Root cause and fix are in the seed findings
below.

**Citation defect, one run in two.** The first run attributed next-term course
offerings and seat counts to `[kuali]`:

> **Available to take:** CYB-410 and CYB-420, both offered with seats available
> (38 and 21, respectively) [kuali].

No kuali tool was called on that request — the audit rows show only
mcp-colleague. The second run cited everything as `[colleague]`, correctly. So
this is model variance rather than a systematic fault, but it is variance that
lands on the demo's citation claim, and it is worth knowing it can happen.

**Audit rows (first run, IDs 850, 854–856, 859–863), all present:**

```
  850  01:11:28  gateway        router_classified  dana  {"intent": "advisee_detail", ...}
  854  01:11:30  mcp-colleague  tool_call          dana  {"tool": "get_student_summary", "args_hash": "30a385fdcf26", "decision": "ok"}
  855  01:11:30  mcp-colleague  tool_call          dana  {"tool": "get_student_degree_progress", "args_hash": "30a385fdcf26", "decision": "ok"}
  856  01:11:30  mcp-colleague  tool_call          dana  {"tool": "get_next_term_options", "args_hash": "30a385fdcf26", "decision": "ok"}
  859  01:11:36  gateway        request_completed  dana  {"tools_used": [...3 tools...], "latency_ms": 9690.7}
  860-863        orchestrator   tool_call ×3 + answer_returned
```

---

## 7. Kim — "Which fast-growing occupations would a Cybersecurity BS graduate qualify for?"

**Expected (SPEC §7.7):** CYB outcomes' skills matched against occupation skills,
producing a strong match, a partial match, and a miss, with `[kuali]` and
`[labor]` interleaved.

**Assessment: FAIL.** Run twice; both runs failed the same way.

The model never called `get_course_outcomes`. It answered from
`get_program_occupation_map`, which is a pre-baked crosswalk table, and read the
mapped occupations straight off it. There is no skills match in the answer,
because the skill tags were never fetched.

**Run 2 reply (the cleaner failure), in full:**

> CYB-BS maps to two occupations, and they sit at opposite ends of the growth
> spectrum.
>
> ### Fast-growing: **Information Security Analysts** (15-1212)
> - **Projected growth:** 32.7% — third-fastest among all tracked occupations [labor]
> - **Median wage:** $120,360 [labor]
> - **Skills:** incident response, network defense, regulatory compliance, risk
>   assessment, security architecture, security auditing, threat intelligence,
>   vulnerability assessment [labor]
>
> ### Slow-growing: **Network and Computer Systems Administrators** (15-1244)
> - **Projected growth:** 3.1% — dead last among all 12 tracked occupations [labor]
> …
> There's also a contextual note: … **Cloud Infrastructure Architects** (15-1241),
> is not mapped to CYB-BS but has 33.8% projected growth … [labor]

`tools_used: ['list_programs_catalog', 'get_program_occupation_map', 'get_occupation', 'list_occupations']`

Not one `[kuali]` marker appears in the body of that answer. The spec's
"`[kuali]` and `[labor]` interleaved" does not happen. Neither does strong /
partial / miss: what the room gets is "one of the two mapped occupations is
growing and the other isn't", which is a lookup, not a synthesis.

Run 1 was marginally better and still wrong. It did call `get_program_curriculum`
and produced this sentence:

> It demands skills like incident response, network defense, security
> architecture, threat intelligence, and vulnerability assessment — all of which
> align well with the CYB-BS curriculum sequence covering Network Defense
> (CYB-210), Threat Detection and Response (CYB-310), Security Architecture
> (CYB-410), and Governance, Risk, and Compliance (CYB-420) [kuali]

That is matching occupation skills against *course titles*. It is precisely the
"fuzzy vibes" that SPEC §5 says the shared controlled vocabulary exists to
replace. Run 1 also mis-cited the CYB-BS→SOC mapping as `[kuali]` when
`get_program_occupation_map` is an mcp-labor tool.

**The tool is not broken.** Called directly, it returns exactly what the
synthesis needs:

```bash
curl -s -X POST http://localhost:8024/mcp -H "Authorization: Bearer $KIM_TOKEN" \
  -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"get_course_outcomes","arguments":{"program_code":"CYB-BS"}}}'
```

```json
{ "program_code": "CYB-BS", "outcomes": [
  { "course_code": "CYB-110", "outcome_id": "CYB-110-O1",
    "text": "Communicate Foundations of Cybersecurity findings that depend on risk assessment.",
    "skill": "risk assessment" }, … ] }
```

And the underlying data supports the beat perfectly — the join was measured
directly against the seed databases:

| Occupation | Growth | CYB-BS covers | CYB-BS misses |
|---|---|---|---|
| Information Security Analysts | 32.7% | all 8 skills | — |
| Cloud Infrastructure Architects | 33.8% | 2 of 7 | cloud architecture, infrastructure automation, containerization, distributed systems, API design |
| Data Scientists | 28.4% | 0 of 7 | all |
| AI/ML Engineers | 35.2% | 0 of 7 | all |
| Network and Computer Systems Administrators | 3.1% | 3 of 6 | infrastructure automation, containerization, cloud architecture |

The strong match, the partial and the miss are all sitting in the database. The
model simply never looks at them.

**Root cause.** `get_program_occupation_map`'s description, which is what the
model chooses from, reads:

> Which occupations each academic program maps to. An occupation absent from
> every program is a catalog gap.

That answers both step 7 and step 8 on its face, so the model stops there.
Meanwhile `get_course_outcomes`'s description —

> Learning outcomes for every course in a program, each tagged with a skill from
> the shared vocabulary.

— never says those tags share a vocabulary *with occupation skills*, so nothing
tells the model the two sets can be joined.

**Proposed fix (not applied — this is a verification pass).** Two changes, both
small, neither touching a static prompt prefix:

1. In `services/mcp-labor/app.py`, retitle `get_program_occupation_map`'s
   docstring so it stops reading like a qualification verdict. Something like:
   *"The administrative crosswalk of program to occupation codes. It records
   which occupations a program was registered against; it is not evidence that a
   graduate's skills match one. For qualification, join `get_course_outcomes`
   skill tags against this occupation's skills."*
2. In `services/mcp-kuali/app.py`, extend `get_course_outcomes`'s docstring to
   name the join: *"…tagged with a skill drawn from the same controlled
   vocabulary as mcp-labor's occupation skills, so the two can be matched by
   exact string."*

If that alone does not hold, add a fifth ground rule to
`services/orchestrator/prompts.py` (still a static constant, so cache discipline
is unaffected) stating that qualification and gap questions are answered by
matching outcome skill tags against occupation skills, and that the
program-occupation map is an index, not evidence.

**Audit rows (run 1, IDs 1002, 1008–1009, 1047–1048, 1049–1055; run 2, IDs
1056–1067), all present.** The audit trail is honest about the failure: row 1066
lists `get_course_outcomes` in `tools_offered` and not in `tools_used`.

---

## 8. Kim — "Which fast-growing occupations have no matching program in our catalog — what could we consider rolling out?"

**Expected (SPEC §7.8):** AI/ML Engineers and Cloud Infrastructure Architects
surface, with the adjacent existing outcomes noted.

**Actual reply (abridged):**

> Two high-growth occupations have no program in our catalog [kuali] [labor]:
>
> ### 1. AI/ML Engineers — 35.2% growth | $136,620 median
> **SOC 15-2099** — skills: machine learning, deep learning, data modeling,
> predictive modeling, statistical analysis, distributed systems, software
> development [labor]
>
> **Existing overlap:** DAT-MS and CS-BS both map to Data Scientists (15-2051),
> which shares data modeling, machine learning, predictive modeling, and
> statistical analysis. The gap is specifically in *deep learning* and the
> engineering deployment side.
>
> ### 2. Cloud Infrastructure Architects — 33.8% growth | $130,390 median
> …
> **Existing overlap:** CYB-BS and IS-MS map to Network/Systems Administrators
> (15-1244), sharing systems administration and network engineering. …
>
> | Option | Approach | Rationale |
> |--------|----------|-----------|
> | **New MS in AI/ML Engineering** | Standalone program targeting 15-2099 | … |
> | **Cloud Computing concentration or MS** | Target 15-1241 | … |
> | **Hybrid: AI & Cloud Infrastructure MS** | Combined program | … |
>
> The next step would be to compare these skill profiles against our existing
> course outcomes in DAT-MS, CS-BS, IS-MS, and CYB-BS to quantify exactly which
> competencies are already taught and which are wholly missing. Want me to run
> that curriculum gap analysis?

`tools_used: ['list_programs_catalog', 'list_occupations', 'get_program_occupation_map', 'get_occupation']`

**Assessment: PARTIAL PASS.** The headline lands and lands well: exactly the two
deliberately unmapped fast-growers surface, in the right order, with growth and
wage figures that match the seed, and the "what could we roll out" table is
genuinely the program-strategy moment the spec is aiming at. The room will get
the point.

The spec's second half — "with the adjacent existing outcomes noted" — does not
happen. `get_course_outcomes` was never called here either. The adjacency the
model reports is occupation-to-occupation (AI/ML shares skills with Data
Scientists, which DAT-MS maps to), not occupation-to-curriculum. The model then
says so itself in its closing line, offering to "compare these skill profiles
against our existing course outcomes" — that is, admitting it did not do the part
the spec asks for.

`[kuali]` appears twice on the strategy table's rationale rows, attached to
claims about what DAT-MS and CS-BS teach. Those claims came from the labor
mapping, not from kuali. The `[kuali] [labor]` pair on the opening line is
defensible, since `list_programs_catalog` is a kuali tool.

Same root cause and same fix as step 7.

**Audit rows: IDs 1068–1079, all present.**

---

## Prompt-cache discipline (SPEC §1)

**Method.** The same question was asked twice through the gateway as the same
persona, and the `answer_returned` rows from the orchestrator and the
`router_classified` rows from the gateway were compared. Per the brief, only
`prompt_cache_hit_tokens` and `prompt_cache_miss_tokens` were used to judge cache
behaviour — `prompt_tokens` is not comparable, because deepseek-v4-flash prepends
its own prompt server-side.

Question: *"What is the projected growth and median wage for Data Scientists?"*,
persona `pat`.

| Run | Service | Event | hit | miss |
|---|---|---|---|---|
| 1 | gateway | `router_classified` | **640** | 148 |
| 1 | orchestrator | `answer_returned` | **1408** | 230 |
| 2 | gateway | `router_classified` | **768** | 20 |
| 2 | orchestrator | `answer_returned` | **1408** | 230 |

**Assessment: PASS, clearly.**

The second run reports nonzero `prompt_cache_hit_tokens` on both services. At the
gateway, hits rose from 640 to 768 and misses fell from 148 to 20 — the static
prefix was already cached, and on the second run the dynamic message tail cached
too. At the orchestrator the two runs are identical at 1408 hits and 230 misses;
the residual 230 misses are the tool result, which is new content on every run by
definition and should never cache.

The stronger evidence is that run 1's gateway call *already* had 640 hits before
the question had ever been asked. That is the static prefix caching across
personas and across questions, which is only possible if nothing dynamic has
leaked into it.

**Across the whole session — 48 model calls, every persona, every step:**

```
rows with ZERO cache hits: 0 of 48
```

Router hits were 640 or 768 on every single call and never anything else, which
is the signature of a genuinely fixed prefix. Orchestrator hits ranged from 640
to 7680, scaling with how many tool schemas the caller's role puts in view — also
expected, since the tool schemas sit inside the cacheable prefix and a dean sees
ten tools where an adjunct sees two.

No action needed. `services/gateway/prompts.py` and
`services/orchestrator/prompts.py` are both module-level constants with no
interpolation, and the numbers confirm it end to end.

---

## Audit coverage

Every step produced audit rows, including all three refusals and the bypass.

| Step | Rows | Includes |
|---|---|---|
| 1 | 734–738 | router, tool_call ok, request_completed, answer_returned |
| 2 | 739–745 | two tool_call ok rows across two MCP servers |
| 3a | 746–747 | **`refused_at_gate`**, no orchestrator or MCP rows |
| 3b | 748–752 | mcp-labor tool_call ok |
| 4 | 753–754 | **`decision: refused`** from mcp-colleague, no gateway rows |
| 5a | 755–761 | two mcp-canvas tool_call ok rows |
| 5b | 797, 799, 801–803 | **`decision: refused`** from mcp-canvas with the §4.6 string |
| 5c | 841–845 | mcp-canvas rollup |
| 6 | 850, 854–856, 859–863 | three mcp-colleague tool_call ok rows |
| 7 | 1002, 1008–1009, 1047–1055; 1056–1067 | kuali and labor tool_calls |
| 8 | 1068–1079 | kuali and labor tool_calls |
| cache check | 1081–1090 | both runs |

The audit viewer serves correctly:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}, %{size_download} bytes, %{content_type}\n" http://localhost:8030/
HTTP 200, 6214 bytes, text/html; charset=utf-8
```

---

## Observations not tied to one step

### O1. One request failed outright with a 500 — an MCP connect timeout

The very first attempt at step 1 returned `Internal Server Error` from the
gateway. The orchestrator log shows:

```
File "/opt/venv/lib/python3.12/site-packages/fastmcp/client/client.py", line 622, in _connect
    raise RuntimeError(
RuntimeError: Client failed to connect: Failed to initialize server session
```

mcp-colleague and mcp-canvas had logged successful `POST /mcp` handshakes; the
third server in `MCP_SERVERS` order did not. An immediate retry of the identical
request succeeded in 10.2 seconds, and the remaining ~15 requests in this session
all succeeded, so the rate is roughly one in sixteen.

This matters because the orchestrator builds fresh MCP clients to **all four**
servers on every request (SPEC §4.3, per-request construction), so any one server
being slow to hand out a session kills the whole request — even when the caller's
role needs none of that server's tools. Dana's question needs only mcp-colleague,
but it died on a different server's handshake.

No fix proposed here beyond flagging it, since it is a Session 3 robustness
question rather than a spec divergence. Worth knowing before a live demo: if a
question 500s, ask it again.

### O2. Audit rows were silently lost when the audit service restarted

During the second run of step 6, three mcp-colleague `tool_call` rows never
reached the audit database. The cause is visible in the logs:

```
audit-1          | 2026-08-09T01:13:12.969Z INFO:  Shutting down
audit-1          | 2026-08-09T01:13:15.464Z INFO:  Application startup complete.
mcp-colleague-1  | 2026-08-09T01:13:13.853Z audit event 'tool_call' dropped: POST http://audit:8030/events failed (ConnectError)
```

The audit service runs under `uvicorn --reload`; the other session editing files
in `services/audit/` restarted it, and for about 2.5 seconds every audit POST
failed. `libs/harness_auth/audit.py` is fire-and-forget with no retry by design,
so those events are gone. The warning line is debounced to once per minute per
process, so one log line stands for all three lost rows.

The design is correct — SPEC §2 is explicit that auditing must never break the
caller — and the warning line did its job. This is exactly the situation
`CLAUDE.md`'s pre-demo check anticipates:

```
pre-demo: docker compose logs audit gateway | tail -20
          Expect NO "audit event ... dropped" lines.
```

The practical note for Session 3: **do not edit files during a rehearsal or a
demo.** A hot-reload of the audit service loses whatever is in flight, and the
receipts moment in step 9 is the one place a hole would be noticed.

---

## Seed data findings

### S1. `get_next_term_options` always returns the courses the student is currently taking

**Severity: blocks demo step 6.**

**What happens.** For S-1042, the current registrations and the next-term options
are the same two courses:

```
$ sqlite3 data/colleague.db "select * from registrations where student_id='S-1042';"
S-1042|CYB-420|2026FA
S-1042|CYB-410|2026FA
```

```json
// get_next_term_options("S-1042")
{ "term": "2027SP",
  "options": [ { "course_code": "CYB-410", "offered_next_term": true, "seats": 38 },
               { "course_code": "CYB-420", "offered_next_term": true, "seats": 21 } ],
  "blocked": [ { "course_code": "CYB-460", "prereqs": ["CYB-410","CYB-420"],
                 "prereqs_satisfied": false } ] }
```

**Why, exactly.** This is structural, not bad luck. In `scripts/seed.py` around
line 511, current registrations are drawn *from* the eligible set:

```python
eligible = eligible_next(student["program_code"], set(completed))
current = random.sample(eligible, min(random.randint(1, 3), len(eligible)))
```

And `get_next_term_options` in `services/mcp-colleague/app.py` builds its options
from `requirement_progress`, which knows only about `completed` — it has no
notion of "currently registered". So a student's in-progress courses are
guaranteed to reappear as next-term options for **every student in the seed**,
not just S-1042. S-1042 is the worst case because the overlap is total: two of
two.

`verify()` in seed.py does assert S-1042 has a good next-term answer, but the
assertion cannot catch this, because it is written in the same terms as the bug:

```python
options = eligible_next(s1042["program_code"], set(s1042["completed"]))
assert len(options) >= 2, "S-1042 needs at least two eligible next-term courses"
```

**Proposed fix — the one I would actually make.** Teach the tool the difference
between "remaining" and "in progress". In
`services/mcp-colleague/app.py::get_next_term_options`, read the student's
current-term registrations and either exclude those courses from `options` or
carry them in a third list alongside `options` and `blocked`. SPEC §4.6 describes
the tool as returning "remaining required courses whose prereqs are met", and a
course the student is sitting in this term is not one that remains to be
scheduled. This also improves the answer for all 300 students, not just S-1042.

**Proposed fix — seed-only, if the service must not change.** Pin S-1042's
profile in `scripts/seed.py` instead of letting the sampler pick, so that the
overlap is partial rather than total:

```python
# Demo moment 6 needs a next-term answer with something genuinely new in it.
# Left to the sampler, S-1042's registrations are drawn from the same eligible
# set the next-term tool reports, so every option is a course he is already in.
PINNED_PROFILES = {
    "S-1042": {"completed": ["CYB-110", "CYB-210", "CYB-240", "CYB-310"],
               "current":   ["CYB-330"]},
}
```

That gives him 12 of 24 credits, one course in progress, and CYB-410 plus CYB-420
as genuinely new next-term options, with CYB-460 still blocked on the prereq
chain. The demo line becomes clean: *"Next term Nathan should take CYB-410 and
CYB-420, both offered with seats. The capstone is blocked until those are done."*

**And strengthen the guard**, so this cannot silently return:

```python
s1042_options = set(eligible_next(s1042["program_code"], set(s1042["completed"])))
assert s1042_options - set(s1042["current"]), (
    "S-1042's next-term options are all courses he is already taking; demo "
    "moment 6 will recommend the schedule he is currently sitting in"
)
```

### S2. Among *fast-growing* occupations there is no partial skill match for CYB-BS

**Severity: contributes to demo step 7.**

SPEC §5 asks for CYB-BS outcomes to "strongly cover Information Security
Analysts' skills and partially cover two others — the qualification demo should
show a strong match, a partial match, and a miss." The seed satisfies that
literally, and `verify()` asserts it:

```python
netadmin = by_title["Network and Computer Systems Administrators"]
assert 0 < len(netadmin & cyb) < len(netadmin), "NetAdmin must be a partial match for CYB-BS"
assert not (by_title["Financial Analysts"] & cyb), "Financial Analysts must be a clean miss"
```

But the demo question asks about **fast-growing** occupations, and neither
designated example is fast-growing. Network and Computer Systems Administrators
grows at 3.1% — dead last of twelve. Financial Analysts grows at 8.2%. The model
correctly excludes both, and the strong/partial/miss trio collapses. Within the
fast-growing set the only partial is Cloud Infrastructure Architects at 2 of 7
skills, which is thin, and it is also needed as an *unmapped* gap occupation for
step 8 — so leaning on it for step 7 muddies both beats.

The seed invariant does not constrain the subset the demo question actually asks
about. That is the gap.

**Proposed fix.** Raise Network and Computer Systems Administrators into the
fast-growing band, in `scripts/seed.py` line 233:

```python
    ("15-1244", "Network and Computer Systems Administrators", 21.5, 95360,
     ["systems administration", "network engineering", "infrastructure automation",
      "containerization", "technical documentation", "cloud architecture"]),
```

Growth 3.1 → 21.5 leaves the skill list untouched and hands step 7 an exact trio
inside the fast-growing set:

| Role in the demo | Occupation | Growth | CYB-BS skill coverage |
|---|---|---|---|
| strong match | Information Security Analysts | 32.7% | 8 of 8 |
| partial match | Network and Computer Systems Administrators | 21.5% | 3 of 6 |
| clean miss | Data Scientists | 28.4% | 0 of 7 |

It also keeps AI/ML Engineers and Cloud Infrastructure Architects as the top two
by growth, so step 8's gap analysis is unaffected. Then tighten `verify()` to
assert the trio holds *among occupations above a growth threshold*, rather than
among all twelve — otherwise this reappears the next time someone tunes growth
numbers.

Note that S2 alone will not fix step 7. The model never fetches the skill tags at
all (finding in §7 above). S2 makes the answer good once it does.

### S3. Minor — BUS-201-B and BUS-201-A have only four students each

SPEC §5 asks for BUS-201-B to be "visibly not" healthy, and it is: mean 16.5 days
since login and 18 missing submissions against CYB-310-A's 1.4 days and 2
missing. But the section holds only four students, so the contrast rests on a
very small n.

Neither section is used in the §7 script — step 5 asks about CYB-310 (8 students,
good texture) and gets refused on BUS-201-A — so this does not affect the demo as
written. It matters only if someone asks about noor's second section during Q&A,
where "three of four students are behind" is a weaker line than it should be.

If it is cheap to do while tuning seeds in Session 3, raise BUS-201-B's
enrollment to eight or ten. Otherwise, leave it.

### S4. Minor — repeated surnames inside one section roster

CYB-310-A's roster reads "Theresa Whitfield, Zachary Whitfield, … Sara Kaur, …
Terrence Kaur", and dana's advisee list contains Christopher Bryant and Emily
Bryant, Krista Leblanc and Terrence Leblanc, Christopher Foley and Tyler Foley,
Christopher Kaur and Sara Kaur. Drawing first and last names independently from
two short lists collides often at n=300.

The names are boring and realistic as SPEC §5 requires, so this is cosmetic. It
is worth thirty seconds only because "Dana Whitfield" is also the advisor
persona's name, and a student surnamed Whitfield appearing in a section roster
during the demo invites a distracting question. Consider removing "Whitfield"
from `LAST_NAMES`, or rejecting a sampled name whose surname matches a persona.

---

## What to fix before the demo, in priority order

1. **Step 7 does not do the synthesis it claims to** (§7 above). Two tool
   docstring edits are the cheapest fix; an orchestrator prompt rule is the
   backstop. Without this, the "Synthesis" claim in SPEC §0 is demonstrated only
   by step 8, and only partially.
2. **Step 6's answer recommends courses the student is already taking**
   (finding S1). Fix the tool, or pin the seed profile.
3. **Seed finding S2**, so that step 7 has a real strong/partial/miss to find
   once it starts looking.
4. **Do not edit files during rehearsal** (observation O2), and run the
   `CLAUDE.md` pre-demo log check.
5. Optional polish: the router's promise of "public curriculum data" to adjuncts
   (step 3a), and the dean answer's offer to cross-reference section rosters
   against an advisee list (step 2).

Everything else in §7 passes, and the security spine of the demo — layered
enforcement, the verbatim refusals, the bypass, the audit trail, and prompt-cache
discipline — is solid.
