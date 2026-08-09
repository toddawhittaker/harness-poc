# SESSION_REPORT — harness-poc Session 4

Demo polish (fourth session). Nine changes, nothing structural, driven by the
Session 3 verifier's findings 1 through 7. Findings 9 and 10 stay declined.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

**Headline:** eight of the nine changes are done and verified. `uv run pytest
tests/ -q` reports **117 passed** (115 before; two new tests were added by
agreement). Findings 2, 3, 4, 5, 6 and 8 are closed with evidence. **Finding 1
is substantially improved but not fully closed, and finding 7 is improved but
relapses intermittently** — both are model-behaviour problems on one demo beat,
both took four prompt iterations, and both are now at the point where further
grinding is the user's call, not mine. Section 4 says exactly where they stand.

Two verifier runs were made. The second is the authoritative record and is
appended to `DEMO_VERIFICATION.md`; two further fixes were made *after* it, and
their spot-check evidence is in §5 below.

---

## 1. Acceptance status per criterion

The brief set four acceptance criteria plus three riders.

| # | Criterion | Status |
|---|---|---|
| 1 | `pytest` green, 115+ | **PASS** — 117 passed in 44.06s |
| 2 | Verifier clean of findings 1–7 | **PARTIAL** — 2, 3, 4, 5, 6 closed; 1 improved, not closed; 7 improved, relapses |
| 3 | Step 2's answer contains zero deliberation sentences | **PASS on the majority of runs, unstable** — see §4 |
| 4 | Diff confined to the named files | **PASS** — ten files, listed in §3 |
| R1 | Take the gateway "public curriculum data" fix as a ninth change | **PASS** — §2.2 |
| R2 | The rule 4 clause stays | **PASS** — kept, §2.1 |
| R3 | Step 8 pre-ruling: narrowing is a PASS if both fast-growers and adjacency survive | **PASS by narrowing** — §2.1, evidence in §4 |

Findings 9 and 10 were not touched, as instructed.

---

## 2. What was done

### 2.1 `services/orchestrator/prompts.py` — findings 1, 7, 8

`SYSTEM_PROMPT` is still one triple-quoted literal. Verified by AST after every
edit (§5.1). It grew from 2403 to 5161 characters.

**Rule 3** (finding 7) gained a prohibition on *offering* a route, not only on
taking one:

> Never offer such a route either: do not invite the person to supply student
> ids, section ids, or rosters, and do not describe what you could pull if they
> did. What a role can see is the answer for that person, not a consolation
> prize — give the aggregate as the finding and do not apologise for its shape.

**Rule 4** gained one clause, kept on the user's explicit ruling (rider 2):
"…and do not turn it into a request for the person to supply the data instead."
This was flagged in the plan as going beyond the letter of finding 7; the user
ruled it is the finding's root cause, because the Session 3 offending sentence
was generated under rule 4's licence to "say what you would need", not under
rule 3.

**Rule 5** (finding 8) gained the grounding constraint:

> Every coverage count must come from a get_course_outcomes result for that
> exact program, fetched in this run: do not carry a count across from a related
> program, and do not state or imply coverage for a program whose outcomes you
> did not fetch. Name the programs you checked rather than counting in one you
> did not.

and, after the first verifier run flagged a residual over-claim, one more
sentence:

> Saying a skill is taught nowhere in the catalog, or missing everywhere, is a
> claim about every program: make it only if you fetched outcomes for every
> program, and otherwise name the programs you checked and confine the claim to
> them.

Rule 5 also gained a specific case after the first verifier run, in rule 1:

> When a question presumes something your tools do not model — "my advisees",
> asked by someone whose tools return programs and cohorts — say that in one
> sentence, answer the nearest question you can ground, and stop. Do not hunt
> for a way round it, do not narrate the hunt, and do not ask the person for ids
> or codes that would let you try again.

**Finding 1 (narration)** went through four shapes. The final one is an
unnumbered block placed *before* the ground rules, so the numbered list is back
to five and every external reference to "rule 3" / "rule 5" — in
`services/orchestrator/app.py`'s `build_toolset` comment, in
`DEMO_VERIFICATION.md`, in `reports/session-2.md` §4 — still reads true:

> THE SHAPE OF EVERY REPLY, before anything else. Your first sentence is the
> answer or the headline finding — never a preamble, never a plan, never an
> inventory of what you hold. Deliberation does not appear in the reply at all:
> no first-person commentary on which tool to reach for, no listing of the tools
> you have, no thinking aloud about what to try next, no expressed uncertainty
> about how to proceed, no correcting yourself mid-answer. Delete any sentence
> opening with "Wait", "Let me", "I need to", "I'll start by", "First I'll",
> "Now I have", "It looks like I don't have", or "I don't have a tool that".
> Never write "I need to start by understanding what tools are available." or
> "Now I have everything I need. Let me compute the skill matches." — write the
> result those sentences were leading up to. Working belongs in the reply where
> it is evidence: a tally like "Information Security Analysts: 8 of 8 skills
> covered", the named skills a program misses, the counts behind a judgement.
> That detail is wanted, and it comes after the finding it supports, never
> before. Something out of reach is one flat sentence of fact, stated once,
> after whatever you can show.
>
> Your last sentence is a finding too. Do not end by offering to go further: no
> "if you can supply student ids, I can…", no "would you like me to drill
> into…", no invitation to hand you codes, ids, or rosters so you can try again.
> Stop when the answer stops.

The second paragraph was added after the second verifier run, which found
finding 7 had relapsed as a *closing* sentence in 3 of 3 step-2 runs.

**Why it is a block and not rule 6.** The plan's risk 1 pre-specified this
escalation. Session 2 had already tried a narration ban in the Style tail and
verified it ineffective; Session 4's first attempt made it numbered rule 6 and
that was also ineffective (evidence in §4). Promoting it above the list, giving
it the verbatim offending sentences, and enumerating the sentence-opening forms
is what moved the needle.

### 2.2 `services/gateway/prompts.py` — finding 3, plus rider 1

This was the hardest change in the session and it went wrong twice before it
went right. The full story is in §4 because the failure is instructive.

Final state, two edits. The plausibility test is now explicitly closed against
reasoning:

> Set plausibly_authorized false when, and only when, the asker holds none of
> the roles listed as plausible for the category you chose. That list is the
> entire test. Do not narrow it by reasoning about how much of a category a role
> would see in practice — a role listed as plausible is plausible, and what it
> actually gets back is settled far below you.

And the refusal sentence names holders as a closed list, plus rider 1's adjunct
clause:

> When you name who holds it, the list is closed and you may add nothing to it:
> an individual student record is held by advisors, by assignment, and by
> faculty for their own sections — those two, and no third. This governs the
> wording of that one sentence; it does not change which roles are plausible for
> a category. Offer only what the asker's own role can actually reach: an
> adjunct holds labor-market data — occupations, wages, projected growth and
> skills — and no curriculum or student data of any kind.

`advisee_detail`'s `Plausible for: advisor, faculty, dean` is **unchanged**.
`ROUTER_PROMPT` is still a single static literal, 2619 characters.

No authorization logic was added to the gateway. Both edits govern the wording
of a courteous sentence and the reading of a list that already existed;
`CLAUDE.md`'s "authorization decisions live ONLY in MCP servers" rule holds.

### 2.3 `SPEC.md` — finding 2

§7 step 6: `S-1042` → `S-1055`. That id only, as instructed. `SPEC.md:142` —
the RBAC refusal example the spec says to "make exact" — still says S-1042 and
was not touched.

### 2.4 `services/mcp-kuali/rules.py` and `app.py` — finding 4

Classification now works by exception **type**, never by message text, in three
tiers, per the user's ruling:

| Tier | Caught | `decision` | `reason` | Tool reply |
|---|---|---|---|---|
| a | `ToolError` — the refusals `refuse()` raises on purpose | `refused` | `str(exc)` | the refusal, relayable |
| b | `UnknownProgram(ValueError)` | `error` | `unknown program code <x>` | the same text |
| c | `Exception` catch-all | `error` | `type(exc).__name__` **only** | a fixed `INTERNAL_ERROR` string |

Tier (c) never puts `str(exc)` in the audit detail — it can carry file paths,
SQL fragments, or whatever the model typed — and never hands the model
infrastructure text to improvise around.

`UnknownProgram` is defined in `rules.py`, so `app.py`'s change is the import
line plus one raise site:

```python
-    raise ValueError(f"no program with code {program_code}")
+    raise UnknownProgram(f"unknown program code {program_code}")
```

One further edit, prompted by the first verifier run's code note: tier (c) used
to `raise refuse(INTERNAL_ERROR)`. It now raises `ToolError(INTERNAL_ERROR)`
directly, because nothing in a file whose point is that refusals mean refusals
should dress a fault up as somebody being told no.

The other three servers carry the identical catch-all-as-refusal shape. Per the
brief they were **not** fixed and are reported instead:
`services/mcp-canvas/rules.py:85-90`, `services/mcp-colleague/rules.py:112-120`,
`services/mcp-labor/rules.py:60-65`.

All four `mcp_auth.py` copies remain byte-identical — one distinct md5,
`937c7753d32da38d1f44f5c505ab3d51` (§5.6).

### 2.5 `services/audit/viewer.html` — finding 5, scoped exception

Three changes and nothing else in `services/audit/`:

1. `limit=100` → `limit=200`.
2. `rowClass()` learns decision values, with an unrecognised decision reading
   neutral rather than green:

```js
const DECISION_CLASS = { ok: "ok", refused: "refused", error: "error" };
...
const decision = ev.detail && ev.detail.decision;
if (decision) return DECISION_CLASS[decision] || "error";
return "ok";
```

3. `--error: #a8b0be` and `tbody tr.error td.event { color: var(--error); }`.

Rows with **no** `decision` field — `router_classified`, `answer_returned`,
`request_completed` — still return `"ok"` and stay green. Verified in §5.4.

The brief said "error renders unclassed". It would not have: `rowClass()`'s
fallback was `"ok"`, so an input error would have been painted the legend's
success green. The user extended the scoped exception to cover this after being
shown the code.

### 2.6 `CLAUDE.md` — scoped exception, three additions

(a) The pre-demo check is now the verifier's version. (b) The seed command now
carries the MCP restart. (c) A new deploy section. Text quoted in §5.5.

One wording correction against the plan: the plan's draft said the post-suite
run "will show two dropped auth_failed events". It shows **one line**, because
drops are debounced to once a minute per process. The committed text says so.

### 2.7 `.env.example` and `docker-compose.yml` — the Chainlit cookie secrets

Both apps used to interpolate the *same* `${CHAINLIT_AUTH_SECRET}`, so the
per-app distinction existed only in the fallback and one `.env` value would have
collapsed them onto a shared secret. Now:

```yaml
CHAINLIT_AUTH_SECRET: ${CHAINLIT_AUTH_SECRET_ADVISOR:-harness-poc-demo-cookie-secret-advisor}
CHAINLIT_AUTH_SECRET: ${CHAINLIT_AUTH_SECRET_EXEC:-harness-poc-demo-cookie-secret-exec}
```

The container-facing key stays `CHAINLIT_AUTH_SECRET` because that is Chainlit's
own name; only the `.env`-facing name is per app, the same shape as
`JWT_AUDIENCE` → `HARNESS_JWT_AUDIENCE`. `.env.example` gains both entries,
**left blank on purpose**: compose reads them with `:-`, so an empty value falls
back to the default rather than handing Chainlit an empty secret. The bare
`CHAINLIT_AUTH_SECRET` stops being read; it was set nowhere in the repo or in
`.env`.

### 2.8 `tests/test_auth.py` — two cases

Added by agreement, taking the suite from 115 to 117. Both assert on
`detail.decision` and a `reason` **prefix**, never the whole message, so they
pin the contract rather than the wording.

- `test_an_unknown_program_code_audits_as_an_error_not_a_refusal` — kim (dean)
  passes `ZZZ-XX` to `get_course_outcomes`; the audit row must read
  `decision: "error"` with a reason beginning `unknown program code`.
- `test_a_role_refusal_still_audits_as_refused` — pat (adjunct) calls the same
  tool with a valid code; the row must still read `decision: "refused"`. This is
  the negative control: `"error"` existing must not have eaten `"refused"`.

---

## 3. The diff

`git diff --stat`, at the end of the session:

```
 .env.example                     |  10 ++++
 CLAUDE.md                        |  23 +++++++--
 SPEC.md                          |   2 +-
 docker-compose.yml               |  12 +++--
 services/audit/viewer.html       |  13 ++++-
 services/gateway/prompts.py      |  23 ++++++---
 services/mcp-kuali/app.py        |  10 +++-
 services/mcp-kuali/rules.py      |  37 +++++++++++++-
 services/orchestrator/prompts.py |  55 +++++++++++++++++----
 tests/test_auth.py               | 101 +++++++++++++++++++++++++++++++++++++++
 10 files changed, 259 insertions(+), 27 deletions(-)
```

Plus `DEMO_VERIFICATION.md` (the Session 4 verifier record) and this file. That
is exactly the amended scope: the brief's eight, plus
`services/mcp-kuali/app.py` and `tests/test_auth.py`, both amended in by the
user during planning.

Session start: `SESSION_REPORT.md` was moved to `reports/session-3.md` and that
move was committed by itself as `684aec8`, per `CLAUDE.md`.

---

## 4. Where findings 1 and 7 actually stand — and the gateway mistake

This section is the honest part and it is the reason the acceptance table says
PARTIAL.

### 4.1 The gateway change broke demo step 2, twice, before it worked

The plan anticipated one half of this and missed the other. It said the
`Plausible for:` list must keep `dean`, because removing it would refuse kim at
the gate and break a step that currently passes. It kept `dean`. But the router
does not only read that list — it reads the whole prompt, and its entire job is
to decide plausibility. **Any sentence anywhere in that prompt saying deans do
not hold advisee detail is read as an authorization fact.**

I wrote two such sentences, one in the `advisee_detail` bullet and one in the
`refusal_message` paragraph. The first verifier run found kim refused at the
gate on 5 of 5 asks, deterministically — audit rows 2152, 2155, 2157, 2159,
2160. SPEC §7.2 wants "program aggregates, no individual names, same harness,
same second"; she got a refusal and the orchestrator was never called.

Removing the bullet clause alone did **not** fix it. My own re-check after that
first revert still showed `tools_used: []` and a gate refusal. The second clause
leaked the same signal.

What worked was to stop describing deans at all and instead:
- state the plausibility rule as a closed lookup — "That list is the entire
  test. Do not narrow it by reasoning about how much of a category a role would
  see in practice";
- state the *holders* positively and as a closed list — "those two, and no
  third" — so deans are excluded by omission rather than by a negation that
  reads like an authorization verdict.

**Verified after the fix, 3 of 3:** kim is routed through, `tools_used:
['get_program_summaries', 'get_program_engagement_rollup']`. The second verifier
run confirmed independently — rows 2447, 2454, 2461, all `router_classified`,
none `refused_at_gate`, and the only three gate refusals in the whole run are
pat's.

**Then removing the "do not name deans" clause reopened finding 3.** The second
verifier run found 2 of 3 pat refusals saying advisee records are "held by
advisors, faculty, **and deans**" (rows 2469, 2475). That is what the closed-list
wording ("those two, and no third") was added to fix, and it did — **3 of 3
clean afterwards**, quoted in §5.2.

The lesson worth carrying: in the router prompt, describing what a role *gets*
is indistinguishable from deciding whether a role *may ask*. Say who holds a
thing, never who does not.

### 4.2 Finding 1, narration: improved a lot, closed on step 2, not on step 7

Four iterations, each measured:

| Attempt | Shape | Step 2 result |
|---|---|---|
| Session 2 (prior) | a clause in the Style tail | verified ineffective, removed |
| Session 4 #1 | numbered ground rule 6 | **137 words** of deliberation, worse than Session 3's 130 |
| Session 4 #2 | unnumbered block before the ground rules | 190–214 word answers; worst opening was one transition clause |
| Session 4 #3 | + rule 1's "question presumes something your tools do not model" case | **zero deliberation, 3 of 3** (verifier), openings quoted in §5.2 |

The second verifier run's measurement of step 2, three asks: "Deliberation
before the first substantive line: **zero on all three.** Totals 179, 185, 279
words." Its verbatim openings:

> A: "Here's the picture across programs, ordered by concern level:"
> B: "I can't see your individual advisees, but here's the picture across
>    programs — two angles on where students are struggling."
> C: "I can't isolate your specific advisees — no tool here maps advisors to
>    students. But here's what I can see across all programs…"

Compare Session 3's opening, which this replaces: *"Wait — I have no tool that
maps an advisor name to their advisees. Let me check if there's anything I
missed."*

**Steps 7 and 8 still open with one narration sentence each** — "Now I can
compare the cybersecurity program's skills…" and "Now let me do the
skill-matching…". The verifier measured step 7 at 271 of 426 words before
"Here's the answer:" and step 8 at 167 of 431, and judged: *"step 8 clears
Session 3's 'survivable' bar and I would ship it. Step 7 does not — 64% of the
reply is scratch paper."*

Session 3's finding 1 itself said steps 7 and 8 getting "a line or two" was
"survivable" and named step 2 as the beat that decides whether the room sees a
product or a chatbot. By that bar step 2 is fixed and step 8 is fine; step 7 is
longer than the finding contemplated.

I checked and excluded one structural explanation: the preamble is not an
artefact of concatenating intermediate agent turns.
`services/orchestrator/app.py:331` returns `result.output`, which is the final
model response only. The preamble is genuinely in the answer text, so it is a
prompt problem, not an assembly problem.

### 4.3 Finding 7: improved, relapses intermittently

Rule 3's "never offer such a route" was ignored by the model 3 of 3 in the
second verifier run — not as a mid-answer offer, which is what Session 3 saw,
but as the *closing* sentence: *"If you can supply student IDs for your
advisees, I can pull section-level detail…"*

The reply-shape block's second paragraph was added for exactly this. My own
four-run spot check afterwards (§5.3): two runs closed cleanly, one closed
"To connect this to your specific advisees, you'd need to supply student IDs or
a section roster", and one stopped short of the aggregates entirely and asked
"Would that be useful?".

So it is better and it is not reliable. **This is where I stopped**, because
four prompt iterations against a variable model is the point at which the next
move is a judgement call about the demo rather than a bug fix. Options, for the
user to choose from, in my order of preference:

1. **Reword demo step 2's question.** Kim asking "which of *my* advisees" is a
   question her role structurally cannot answer, so the model is always one step
   from flailing. "Which programs show students struggling this term?" gets the
   same contrast — dana sees people, kim sees programs — with no impossible
   premise. Cheapest and most reliable, costs one line in SPEC §7.2 and one
   Chainlit starter.
2. **`AGENT_THINKING=true`.** The model narrates because with thinking off it
   has nowhere else to reason. Session 2 measured this at roughly 33 seconds,
   against SPEC §1's latency default. It would likely close steps 2 and 7 at
   once.
3. **Keep iterating on the prompt.** Diminishing, and each iteration costs a
   verifier run.

I did not take any of these: 1 and 3 are outside the brief's nine changes, and 2
reverses a SPEC §1 default.

### 4.4 Step 8, the pre-ruling (rider 3)

**It narrowed, which the user pre-ruled a PASS.** Four `get_course_outcomes`
calls (audit rows 2549–2552), four programs claimed about — CS-BS, DAT-MS,
IS-MS, CYB-BS — and every claim names them. Both unmapped fast-growers still
surface (AI/ML Engineers 35.2%, Cloud Infrastructure Architects 33.8%) and the
adjacency story is intact through to the recommendation, so the pre-ruling's
conditions are met. The verifier also confirmed the "missing anywhere / union
across all programs" over-claim from the first run is **gone**.

The tallies survived rule 6 with no over-suppression, which was the plan's
biggest risk: "8 of 8 skills covered" for Information Security Analysts, the
three named misses for Network and Computer Systems Administrators at 3 of 6,
AI/ML Engineers at 0 of 7, `[kuali]`/`[labor]` interleaved. The verifier checked
every number against `data/kuali.db` and `data/labor.db`.

---

## 5. Evidence

### 5.1 Static prompt prefixes, by AST

Run after every prompt edit. `CLAUDE.md`'s hard rule and SPEC §1 require these
to be plain constants; nothing in the committed test suite checks it.

```
$ python3 - <<'EOF'
  ... assert the module-level assignment's value is a single ast.Constant str
SYSTEM_PROMPT: STATIC, 5161 chars
ROUTER_PROMPT: STATIC, 2619 chars
```

Prompt-cache consequence, measured by the verifier: 38 model calls across the
second run, **zero with zero cache hits**. Discipline intact.

### 5.2 Step 3a, after the closed-list fix — 3 of 3 clean

Every run names advisors and faculty, no deans, and promises no curriculum data:

> Individual student records and advising details are held by advisors, and by
> faculty for their own sections—those aren't available to an adjunct. What you
> can reach instead is public labor-market data: occupations, wages, projected
> growth, and skills.

> Information about named or individual students is held by advisors and by
> faculty for their own sections. As an adjunct, you have access to public
> labor-market data — occupations, wages, projected growth, and skills.

> Individual advisee progress is held by advisors, by assignment, and by faculty
> for their own sections. As an adjunct, you can reach public labor-market data
> — occupations, wages, projected growth, and skills — if that would help.

Compare Session 3's: *"Advisee-level detail is held by advisors, faculty, and
deans."* Finding 3 and rider 1 are both closed.

### 5.3 Step 2, after the closing-offer ban — four runs

```
run 1  first = I don't have access to advisor-student relationships, so I can't identify your specific advisees...
       tail  = The closest I can offer is a program-level engagement rollup... Would that be useful?
run 2  first = Here's what stands out across programs this term:
       tail  = ...but these are the trouble spots worth looking at first.
run 3  first = Here's what I can see across all programs, since I can't isolate your individual advisees:
       tail  = To connect this to your specific advisees, you'd need to supply student IDs or a section roster...
run 4  first = I don't have access to a tool that shows your advisees, Kim...
       tail  = Would any of that help?
```

Runs 2 and 3 lead with the answer; runs 1 and 4 lead with the limitation and
then under-deliver on the aggregates. Runs 1, 3 and 4 end with some form of
offer. This is the instability described in §4.3.

### 5.4 Finding 4, both directions, by curl

Tool replies:

```
kim (dean), bad code ZZZ-XX:
  "Error executing tool get_course_outcomes: unknown program code ZZZ-XX"
pat (adjunct), valid code CYB-BS:
  "Error executing tool get_course_outcomes: get_course_outcomes requires the advisor, faculty or dean role."
```

Audit rows:

```
  2126  pat   get_course_outcomes  decision=refused  reason=get_course_outcomes requires the advisor, faculty or dean role.
  2125  kim   get_course_outcomes  decision=error    reason=unknown program code ZZZ-XX
  2118  pat   get_course_outcomes  decision=refused  reason=get_course_outcomes requires the advisor, faculty or dean role.
  2117  kim   get_course_outcomes  decision=error    reason=unknown program code ZZZ-XX
```

Confirmed from the installed SDK that the tool-reply half needs no extra work:
every tool exception is wrapped at `mcp/server/fastmcp/tools/base.py:117` into
`ToolError(f"Error executing tool {name}: {e}")` and returned with `isError`, so
the two cases are distinguishable by message alone.

Viewer behaviour, `rowClass()` replayed over 200 live rows:

```
rows fetched at limit=200: 200
Counter({'failed': 114, 'ok': 70, 'refused': 14, 'error': 2})
 error row -> 2125 mcp-kuali tool_call error
unknown decision -> error      # a decision nobody defined reads neutral, not success
no decision at all -> ok       # router_classified / answer_returned stay green
```

Contrast of every event colour against `--bg #12151c`, WCAG AA floor 4.5:1:

```
--error    #a8b0be  8.37:1  AA
--dim      #8b95a8  6.06:1  AA
--ok       #4ade80  10.48:1 AA
--refused  #fbbf24  10.94:1 AA
--failed   #f87171  6.60:1  AA
--text     #e6e9f0  15.03:1 AA
```

Served page: `HTTP 200, 6792 bytes, text/html; charset=utf-8`, containing
`limit=200`, `--error: #a8b0be`, and the `DECISION_CLASS` map.

### 5.5 The new pre-demo check

Committed text in `CLAUDE.md`:

```
- pre-demo: docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
Expect "clean". Run it AFTER the test suite, never during: the disruptive
test stops the audit service on purpose, so a run within 30 minutes of the
suite shows an expected auth_failed drop from the gateway. Anything else
means demo moment 9's audit page will be missing rows; the line names the
service and the URL that failed. Drops are debounced to once a minute per
process, so one line can stand for several lost events.
```

Run immediately after the suite, as predicted:

```
$ docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
gateway-1        | audit event 'auth_failed' dropped: POST http://audit:8030/events failed (ConnectError)
```

That is the disruptive test doing its job. The verifier independently confirmed
**zero events dropped at or after 04:15:00**, so the second run's receipts are
complete and step 9 is safe.

### 5.6 Suite, scope and invariants

```
$ uv run pytest tests/ -q
117 passed in 44.06s

$ md5sum services/mcp-*/mcp_auth.py | awk '{print $1}' | sort -u
937c7753d32da38d1f44f5c505ab3d51        # one hash, four files — byte-identity holds
```

### 5.7 Regression checks from the second verifier run

- **Step 1** PASS. Step 4 (the bypass) PASS. Step 5a PASS 3/3. Step 5c PASS on
  the claim, with no finding-7 offer. **Step 6** PASS, about Leon Cline /
  S-1055, zero narration, and SPEC now agrees.
- All four spec-fixed refusal strings verbatim at the tool layer, rows
  2575–2578.
- Two apps visibly distinct, light on 8080 and dark on 8081.
- The script now writes 76 rows against the viewer's 200, leaving 124 rows of
  headroom where Session 3 had 24. Finding 5 closed.

---

## 6. Deviations from the plan

1. **Two extra edits to `services/gateway/prompts.py` and
   `services/orchestrator/prompts.py`** beyond what the plan described, both
   inside files already in scope, both forced by verifier findings: the
   closed-list holder wording (§4.1) and the closing-offer ban (§4.3). No new
   file was touched.
2. **Rule 6 is not a numbered rule.** The plan proposed it as ground rule 6; it
   is an unnumbered block before the list instead. This was the plan's own
   pre-specified escalation for the case where the numbered form failed, which
   it did. Side benefit: the ground rules stay at five, so every external
   reference to rule numbers still reads true.
3. **One extra edit to `services/mcp-kuali/rules.py`**: tier (c) raises
   `ToolError(INTERNAL_ERROR)` rather than `refuse(INTERNAL_ERROR)`, on the
   verifier's code note. Same file, same finding.
4. **One extra sentence in rule 5**, closing the "missing anywhere in the
   catalog" over-claim the first verifier run found. Same file, same finding.
5. **The plan's CLAUDE.md wording was wrong** about the post-suite check showing
   "two dropped auth_failed events"; it shows one debounced line. Corrected in
   the committed text.
6. **The rule 4 clause was kept**, on the user's explicit rider 2 ruling. The
   plan had offered to drop it.

---

## 7. Open questions

1. **Findings 1 and 7 on step 2 and step 7.** §4.3 lists three options —
   reword the demo question, flip `AGENT_THINKING`, or keep iterating. All three
   are outside the brief. Which one?

2. **Step 7 spends 271 of 426 words on working before the answer.** The verifier
   would not ship it; Session 3's finding called a line or two "survivable" but
   this is more than that. Same three options as above.

3. **New findings from the second verifier run, none acted on.** Each names its
   file and change:
   - **Counting errors.** Step 7 produced a self-contradicting tally ("1 of 7
     skills covered: only *distributed systems* is not covered, and in fact none
     of their skills appear"); the true value is 0 of 7. A repeat gave Cloud
     Infrastructure Architects as 3 of 7 when it is 2 of 7, and Financial
     Analysts as 0 of 5 when it has six skills. Step 8 said a CS-BS + IS-MS
     union covers 6 of 7 when it is 5 of 7, and contradicted itself four lines
     later. Step 1 opened "Five of your advisees are clearly struggling" and
     then named nine. Fix: a constraint in
     `services/orchestrator/prompts.py` that any stated count must equal the
     number of items named.
   - **Citation-marker errors.** Step 5c cited all eleven facts `[kuali]` when
     the data came from canvas and colleague; step 5b cited the §4.6 refusal
     `[colleague]` 3 of 3; step 7 cited the crosswalk `[kuali]` when
     `get_program_occupation_map` is an mcp-labor tool. Fix: one rewrite of rule
     2's marker definitions.
   - **Step 5b is unstable because of seed adjacency.** noor teaches `CYB-310-A`
     and `BUS-201-B`, one character from `BUS-201-A`, the section the demo needs
     her refused for. One run never called the tool at all and answered about
     BUS-201-B instead, so no refusal row was written and demo moment 5 lost its
     point. Fix: in `scripts/seed.py`, give noor `CYB-210-A` instead of
     `BUS-201-B` and hand `BUS-201-B` to `fac-005`, who already holds
     `BUS-201-A`.
   - **The model guesses bad program codes on step 7.** Both runs' first kuali
     call used an invented code — `CBS`, then `CYBERBS` (rows 2534, 2566) —
     producing a grey error row on the flagship synthesis slide every time. Now
     visible rather than mislabelled amber, which is finding 4 working as
     intended, but it should not happen. Fix: call `list_programs_catalog`
     before `get_course_outcomes`.

4. **The catch-all-as-refusal shape in the other three MCP servers**
   (`services/mcp-canvas/rules.py:85-90`,
   `services/mcp-colleague/rules.py:112-120`,
   `services/mcp-labor/rules.py:60-65`). Reported, not fixed, as instructed. It
   deserves its own pass.

5. **Nothing is committed.** All ten files plus `DEMO_VERIFICATION.md` and this
   report are in the working tree. Say the word and I will commit; the only
   commit made this session is `684aec8`, the Session 3 report move.
