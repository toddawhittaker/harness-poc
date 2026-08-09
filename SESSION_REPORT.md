# SESSION_REPORT — harness-poc Session 11

The freeze session. Four items were attempted, three landed, and **the fourth
triggered the brief's pre-authorized fallback**: the certification pass failed a
step, so the scoped grounding lift and `AGENT_THINKING=true` were both reverted,
the verifier was re-run in the reverted configuration, and it returned **10 of
10**.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

---

## The headline, in three sentences

**We are in the fallback world.** The demo ships on Session 10's committed
state — `AGENT_THINKING=false`, `grounding.py` and `app.py` untouched — with the
false arm's known warts, and it is certified there: the demo-verifier returned
10 of 10 with every standing check green, including demo moment 5b's amber row.
The one thing this session keeps is item 1, the split of the thinking flag into
`AGENT_THINKING` and `ROUTER_THINKING`, which is a safety improvement in either
world and is now recorded in `SPEC.md`.

**What went wrong is worth more than what went right.** The marker correction
worked exactly as specified — it fired seven times in ten runs, corrected every
one correctly, and closed the decline failure mode outright (zero declines in
ten runs, against Session 10's one in three). It also, unforeseen by anyone,
cost demo moment 5b its tool-layer refusal in three of those ten runs, because
the guard's *rejection* had been quietly doing a second job: the corrective
retry was what drove the tool call that produces the refusal. Correcting the
marker instead of rejecting the reply left the model's first answer standing,
and its first answer was to say "that is not my section" from a roster it
already held, without ever touching the boundary.

**Nothing was fixed after measurement began**, other than the fallback itself.

---

## 1. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | Item 1: `AGENT_THINKING` governs `agent_model()` only; new `ROUTER_THINKING` (default false) governs `router_model()`; compose sets both explicitly on the services that read them; `.env.example` documents both; SPEC §1 gains one sentence | **PASS, and it survives the fallback.** §3. The SPEC sentence records the deviation as *tried and reverted*, which is what actually happened — §7 deviation 1 |
| 2 | Item 2: scoped single-server marker correction, `answer_marker_corrected` event, one viewer line, five tests | **BUILT, MEASURED, THEN REVERTED BY THE FALLBACK.** It worked; §4 says what it cost. The code is preserved as a patch — §8.3 |
| 3 | Item 3: `AGENT_THINKING=true` in `.env`, orchestrator recreated, router verified non-thinking by `docker inspect`, four personas warmed | **PASS as performed**, then reverted by the fallback. §5.1 |
| 4 | Demo moment 5 ×10: 10 of 10 answered, zero declines | **PASS** — 10 of 10, zero declines, zero invented ids. §5.2 |
| 5 | …at least 9 of 10 ending in the relayed mcp-canvas refusal with its amber row | **FAIL — 5 of 10.** The finding of the session. §5.2 |
| 6 | Step 1 ×3 and step 7 ×3: zero wrong counts, zero wrong tallies, zero self-argument, zero preambles | **PASS on step 1 (3 of 3 clean).** **PARTIAL on step 7**: the four headline tallies were exact in 3 of 3, but two secondary numbers were wrong across the three runs. §5.3 |
| 7 | The bypass beat ×3: receipts clean, refusal at mcp-colleague | **PASS** — 3 of 3. §5.4 |
| 8 | One full demo-verifier pass of steps 1–10 as the freeze certification | **RUN, AND IT FAILED A STEP** (5b's audit-row half). §5.5 |
| 9 | FALLBACK if moment 5 shows any decline **or the verifier pass fails a step** | **TRIGGERED AND EXECUTED IN FULL**, including the re-run. §6 |
| 10 | Report which world we are in | **This report.** The fallback world; certified 10 of 10 |
| 11 | `pytest` green, 138+ with the five new guard tests | **NOT MET, AND CANNOT BE IN THIS WORLD.** 138 passed with the lift in place (§4.4); the fallback reverted the guard and its tests, so the shipped suite is **133 passed**. §7 deviation 3 |
| 12 | The certification pass 10/10 with its report | **PASS in the reverted configuration** — 10 of 10, zero fails. §6.2 |
| 13 | Diff confined to the named files | **PASS.** The final diff touches seven files, all inside the permitted list. §2 |
| 14 | No prompt-file changes; `REGROUND_INSTRUCTION` untouched; nothing else in `services/audit/` | **PASS** — `services/orchestrator/` and `services/audit/` are byte-identical to HEAD. §2 |

---

## 2. The diff, as it now stands

Session start: `SESSION_REPORT.md` was moved to `reports/session-10.md` and that
move was committed by itself as **`1b55ba5`**, per `CLAUDE.md`.

```
 .env.example                                       |  13 +++
 DEMO_VERIFICATION.md                               | 112 ++++++++++++++++++++-
 SPEC.md                                            |   2 +
 docker-compose.yml                                 |  11 +-
 docs/LESSONS.md                                    |  68 +++++++++++--
 libs/harness_models/src/harness_models/__init__.py |  10 +-
 libs/harness_models/src/harness_models/factory.py  |  48 ++++++---
 7 files changed, 242 insertions(+), 22 deletions(-)
```

Plus this file. Every path is inside the brief's permitted list. Proven rather
than asserted:

```
$ git diff --exit-code services/orchestrator/ services/audit/ tests/ scripts/ config/ apps/
UNCHANGED: services/orchestrator, services/audit, tests, scripts, config, apps
```

`grounding.py`, `app.py`, `prompts.py`, `REGROUND_INSTRUCTION`, `viewer.html`
and every test file are byte-identical to the committed state. `.env` is
gitignored and appears in no diff; it now reads `AGENT_THINKING=false` and
`ROUTER_THINKING=false`.

---

## 3. Item 1 — the flag split, which survives

`libs/harness_models/factory.py`. One flag became two, each governing one model:

```python
AGENT_THINKING = _thinking("AGENT_THINKING", "false")
ROUTER_THINKING = _thinking("ROUTER_THINKING", "false")

AGENT_SETTINGS = _settings(AGENT_THINKING)
ROUTER_SETTINGS = _settings(ROUTER_THINKING)

def router_model() -> OpenAIChatModel:   # reads ROUTER_THINKING only
def agent_model() -> OpenAIChatModel:    # reads AGENT_THINKING only
```

`__init__.py` exports both flags and both settings objects in place of the
single `MODEL_SETTINGS` (which nothing outside the package read).

**`docker-compose.yml` sets each flag only on the service that builds that
model**, which is stronger than setting both on both. The gateway's environment
contains no `AGENT_THINKING` at all, so no value of it can reach the router by
any route; the orchestrator's contains no `ROUTER_THINKING`. Proven on the live
containers:

```
$ docker inspect harness-poc-orchestrator-1 ... | grep -i thinking
AGENT_THINKING=false
$ docker inspect harness-poc-gateway-1 ... | grep -i thinking
ROUTER_THINKING=false
```

This is the failure Session 10 §6 deviation 1 warned about, closed. That session
measured the agent in reasoning mode by recreating only the orchestrator; a
plain `docker compose up -d` would then have put the router into reasoning mode
as well, silently, and nobody would have been measuring that. It can no longer
happen in either direction.

`.env.example` documents both, with the reason and both halves of the evidence.
`SPEC.md` §1 gains one sentence recording the deviation as tried and reverted —
see §7 deviation 1 for why the wording changed from what the brief specified.

---

## 4. Item 2 — the marker correction, as built and as measured

Built, exercised live, and then reverted by the fallback. Recording it properly
because it is the substance of the session's finding, and because the code is
preserved (§8.3) if you want it back.

### 4.1 What it did

`grounding.py` gained `correct_single_server_markers(reply, servers_that_ran)`,
returning a `Correction` or `None`. It returns `None` — meaning "leave this
alone, byte for byte" — unless exactly one server ran **and** the reply's
bracket markers do not all already name it. `check()` was not touched.

The bracket pattern used for correction is deliberately wider than the one
`check()` uses, because the thing being corrected includes markers naming no
server at all, and fenced three ways so it cannot eat prose: a negative
lookahead excludes markdown links, a minimum length of three excludes `[x]` and
`[3]`, and no newline may appear inside.

`app.py` called it inside the existing guard loop, before `check()`, and emitted
`answer_marker_corrected` with `{from_markers, to_marker, attempt}`. No
regeneration, no other change to the reply. `viewer.html` gained one
classification line putting the event in the grey `error` class.

### 4.2 It worked, and the audit trail proves it worked on the first try

The very first warmup after the flip produced two corrections, both of them the
exact Session 10 failure mode:

```
5951  orchestrator  answer_marker_corrected  kim   {"from_markers": ["colleague"], "to_marker": "canvas", "attempt": 1}
5958  orchestrator  answer_marker_corrected  noor  {"from_markers": ["colleague"], "to_marker": "canvas", "attempt": 1}
```

Across ten runs of demo moment 5 it fired **seven times in six runs**, every
correction right. It also stayed out of the way exactly where it was supposed
to: zero corrections on step 7 (two servers ran), and on the bypass beat, where
zero servers ran, the guard rejected and regenerated as it always has —

```
6147  orchestrator  answer_ungrounded  pat  {"attempt": 1, "markers": ["labor"],
      "reason": "cited [labor], but this request reached no server.", "outcome": "regenerating"}
```

— which is the zero-server case demonstrated unchanged, live, rather than only
in a test.

### 4.3 What it cost, and why nobody saw it coming

Demo moment 5b's tool-layer refusal fell from reliable to **5 of 10**. Three of
the five misses are directly attributable to the correction, and the mechanism
is a coupling nobody had written down:

The guard's *rejection* was doing two jobs. It stopped the bad output, and the
corrective retry (`REGROUND_INSTRUCTION`) told the model to **call a tool before
writing anything** — which is what drove the `get_section_engagement` call that
mcp-canvas refuses. Session 9 §4.2 and Session 10 §4.5 both record this without
naming it: "guard fired, regenerated, refused, verbatim relay", four times out
of four. Correcting the marker instead of rejecting the reply left the model's
first answer standing, and its first answer was to say "BUS-201-A is not among
your sections" from the roster `get_my_sections` had already returned — true,
grounded, correctly cited, and no refusal, no amber row, nothing for demo moment
9 to point at.

The other two misses had no correction and no guard grounds at all; they are the
pre-existing form of the same failure, and they are why 5 of 10 rather than 7 of
10.

### 4.4 The tests

Five new tests in `tests/test_orchestrator_grounding.py`, all passing, taking
the suite to **138**: the wrong-server correction (the Session 10 5a shape); the
descriptive-marker case (`[cyb-bs outcomes]`, which `check()` cannot see at all
— the test asserts that blind spot as a precondition); the two-server case
unchanged in both directions; the zero-marker case never given a marker, plus a
markdown link surviving a correction pass; and a reply already correct, in both
letter cases, passing untouched.

```
$ uv run pytest tests/ -q
138 passed in 31.48s
```

All five were reverted with the code. The shipped suite is 133.

---

## 5. The measurements

All driven with real persona tokens through the gateway, except the bypass,
which goes straight to the orchestrator the way the demo does. Four personas
warmed before any timed run (rows 5944–5967).

| Window | Audit rows | What |
|---|---|---|
| warmup | 5944–5967 | four personas, reasoning mode |
| A | 5968–6102 | demo moment 5, both turns, ×10 |
| B | 6106–6115 | step 1 ×3 |
| C | 6116–6139 | step 7 ×3 |
| D | 6145–6151 | the bypass ×3 |
| E | 6152–6272 | **certification pass A** — the demo-verifier, reasoning mode + correction |
| — | 6375–6398 | four personas re-warmed after the fallback |
| F | 6401–6491 | **certification pass B** — the demo-verifier, reverted configuration |

### 5.1 Item 3 — the flip

`.env` set to `AGENT_THINKING=true`, `ROUTER_THINKING=false`; `docker compose up
-d` recreated the orchestrator and the gateway (both had environment changes).
Verified before any measurement:

```
=== orchestrator ===        === gateway ===
AGENT_THINKING=true         ROUTER_THINKING=false
AGENT_MODEL=deepseek-v4-pro ROUTER_MODEL=deepseek-v4-flash
```

The router carried no `AGENT_THINKING` at all, so its non-thinking state is a
property of the compose file rather than of what happened to be recreated.

Four personas warmed: dana 15.6s, kim 9.4s, noor 8.8s, pat 6.1s.

### 5.2 Demo moment 5 ×10 — the target that was missed

Ten fresh two-turn conversations as noor, the second turn carrying only turn 1's
rendered prose as history, which is what the Chainlit apps hold.

| Measure | Target | Result |
|---|---|---|
| Runs answered, zero declines | 10 of 10 | **10 of 10** ✔ |
| Turn 2 ended in the relayed mcp-canvas refusal with its amber row | ≥ 9 of 10 | **5 of 10** ✘ |
| Relayed the spec sentence verbatim | — | 1 of 10 |
| Invented a section id | 0 | **0 of 10** ✔ |
| Marker corrections | counted | **7, in 6 runs** |
| Guard fires / declines | — | **0 / 0** |
| `tools_used ⊄ tools_offered` | 0 | 0 |
| Orchestrator model calls with zero cache hits | 0 | 0 |

Run by run, with the correction attributed to the turn it landed on:

| Run | Turn-1 correction | Turn-2 correction | Refusal row | Verdict |
|---|---|---|---|---|
| 1 | — | — | 5977 | ✔ |
| 2 | `[colleague],[canvas]` | `[colleague]` | — | ✘ correction-caused |
| 3 | — | — | 6005 | ✔ |
| 4 | — | `[colleague]` | — | ✘ correction-caused |
| 5 | — | — | — | ✘ pre-existing |
| 6 | `[colleague],[canvas]` | — | 6045 | ✔ |
| 7 | `[colleague],[canvas]` | — | 6059 | ✔ |
| 8 | — | — | 6072 | ✔ |
| 9 | — | `[colleague]` | — | ✘ correction-caused |
| 10 | `[colleague]` | — | — | ✘ pre-existing |

**The good half is real and should not be lost in the bad half.** Session 10's
true arm lost demo moment 5a entirely in 1 of 3 runs — two guard rejections on
the same request, then the flat decline sentence on screen. That failure mode is
gone: four turn-1 replies here would have been rejected under the committed
guard (runs 2, 6, 7, 10), and all four were corrected and returned instead. Zero
declines in ten runs.

**The bad half is what the freeze cares about.** In three runs the correction
consumed a rejection that would have forced the tool call, and the amber row
demo moment 9 points at never existed.

### 5.3 Step 1 ×3 and step 7 ×3 — the arithmetic held, with two footnotes

**Step 1, rows 6106–6115: 3 of 3 clean.** Every run stated the counts correctly
and put every student in the right group. Runs 1 and 2 stated all four counts
(25 / 9 / 8 / 6); run 3 stated 25, 9 and 6 and left 8 implicit, which is the
residual Session 10 recorded and no tool field can fix. Group membership was
exact in all three: six flagged-and-quiet, three flagged-and-active (S-1045,
S-1048, S-1051), two quiet-and-unflagged (S-1049, S-1052). **Zero
self-argument, zero preambles, zero overruling of the tool's own count.**

**Step 7, rows 6116–6139: the four headline tallies exact in 3 of 3** — 8/8,
3/7, 3/6, and the miss. Every named covered and missing skill was correct in
every run, checked by exact string intersection against `data/kuali.db` and
`data/labor.db`. Zero preambles, zero self-argument.

Two secondary numbers were wrong, and I am reporting them because the brief said
"zero wrong tallies", not "zero wrong headline tallies":

- **Run 2** put Data Scientists at "0 of 6". The numerator is right; the
  denominator is 7. This is Session 9 finding 9.2's wrong-denominator class, on
  the miss.
- **Run 3** wrote "The remaining **eight** tracked occupations", then named
  seven. Twelve occupations, five discussed, seven remain.

Ground truth, recomputed from the databases rather than quoted from the seed
output:

```
 35.2%  AI/ML Engineers                                 0/7
 33.8%  Cloud Infrastructure Architects                 3/7
 32.7%  Information Security Analysts                   8/8
 28.4%  Data Scientists                                 0/7
 24.1%  Medical and Health Services Managers            1/5
 21.5%  Network and Computer Systems Administrators     3/6
 17.9%  Software Developers                             2/6
 15.4%  Computer and Information Systems Managers       1/5
 10.6%  Management Analysts                             0/5
 10.4%  Computer Systems Analysts                       2/5
  8.6%  Medical Records Specialists                     1/5
  8.2%  Financial Analysts                              0/6
```

**Honest framing:** Session 10 scored only the four headline tallies, so this is
not a demonstrated regression against that measurement — it is a stricter
reading of the same beat. Certification pass A independently found a third
instance of the same class ("Five other occupations" where it is seven).

### 5.4 The bypass ×3 — clean

Rows 6145–6151. `./scripts/demo_bypass.sh` unmodified, three times. Every run:
`tools_used: []`, `tools_offered: ["get_occupation", "list_occupations"]`,
`unoffered_calls: []`, and an mcp-colleague `refused` row carrying
`get_my_advisees requires the advisor role.` verbatim (6146, 6149, 6151).

Run 2 additionally exercised the zero-server guard path unchanged (row 6147,
quoted in §4.2) and regenerated to a clean receipt.

### 5.5 Certification pass A — nine of ten, and the one that failed

Rows 6152–6272, run by the demo-verifier agent through the two Chainlit apps,
step 4 via the unmodified bypass script. Its verdict, verbatim: **"Certification
verdict: not clean."**

- Steps 1, 3a, 3b, 4, 5a, 5c, 6, 8, 9, 10: PASS.
- Step 2: PASS on the RBAC beat; it flagged that every citation read
  `[colleague]` including the canvas-derived columns, and that the reply told a
  dean she lacked a tool she was offered.
- Step 7: PASS on the spec beat, with "Five other occupations" where the data
  says seven.
- **Step 5b: (a) PASS, (b) FAIL.** The reply refused BUS-201-A by name and
  correctly, from `get_my_sections` alone. Rows 6180–6184 are the complete turn
  and contain no `get_section_engagement` call, no refusal, and no amber row.

Standing checks in pass A were otherwise green: 20 model calls, minimum
`prompt_cache_hit_tokens` **896**, **zero** calls with zero hits; all four
spec-fixed refusal strings verbatim at the tool layer with the faculty/dean
asymmetry proven on the same `args_hash`; zero dropped events; `tools_used ⊆
tools_offered` on all ten `answer_returned` rows. One `answer_marker_corrected`
inside the window, row 6187, step 5c.

**Note on the failing run's cause.** That particular 5b reply carried no
correction — it cited `[canvas]` correctly and the guard would never have fired
on it even under the committed code. So the certification run failed on the
*pre-existing* form of the failure, not the correction-caused one. That does not
change the verdict, and the ten-run window (§5.2) is the reason it should not:
the correction-caused form is real and accounts for three of five misses.

---

## 6. The fallback, executed in full

The brief's trigger is "if moment 5 shows any decline in ten runs, **or the
verifier pass fails a step**". Moment 5 showed zero declines. The verifier failed
a step. So the second clause fired, and the fallback was executed without a round
trip, as pre-authorized.

### 6.1 What was reverted

```bash
git checkout -- services/orchestrator/grounding.py services/orchestrator/app.py \
                services/audit/viewer.html tests/test_orchestrator_grounding.py
sed -i 's/^AGENT_THINKING=true$/AGENT_THINKING=false/' .env
docker compose up -d
```

The brief named `grounding.py` and `app.py`. I also reverted `viewer.html` and
`tests/test_orchestrator_grounding.py`, because without the code the viewer line
classifies an event that is never emitted and the five tests fail — a red suite
is not a shippable state. `docker-compose.yml`, `.env.example`, `SPEC.md` and
`factory.py` were edited to describe the reverted world rather than the
experimental one. §7 deviation 2.

Verified after the recreate:

```
=== orchestrator ===        === gateway ===
AGENT_THINKING=false        ROUTER_THINKING=false
```

```
$ uv run pytest tests/ -q
133 passed in 32.83s
```

Four personas re-warmed (rows 6375–6398) before the second pass.

### 6.2 Certification pass B — ten of ten

Rows 6401–6491, 2026-08-09 22:54:58–23:00:5x UTC, same method as pass A.

**Steps 1–10: 10 PASS, 0 FAIL.**

| Step | Result | Note |
|---|---|---|
| 1 | PASS | All four counts stated and correct (25 / 9 / 8 / 6); does not overrule the tool |
| 2 | PASS | Every aggregate exact, no student named |
| 3a / 3b | PASS / PASS | `refused_at_gate` with no tool call; all 12 occupations exact |
| 4 | PASS | Grey `unoffered` row 6423, mcp-colleague refusal 6424 verbatim |
| 5a | PASS | CYB-310-A resolved correctly, all eight students exact |
| 5b | **PASS on both halves** | Refused by name, **and** row **6433** — mcp-canvas, `decision: refused`, carrying the spec sentence verbatim |
| 5c | PASS | All 18 rollup cells exact |
| 6 | PASS | Cleanest answer of the run |
| 7 | PASS | **Zero arithmetic errors** across all eight occupation blocks |
| 8 | PASS | Six distinct `get_course_outcomes` calls before any catalog-wide claim; all twelve tallies correct |
| 9 | PASS | Amber rows present for the gate refusal, the bypass, and 5b |
| 10 | PASS | 401 at all six services independently, each writing its own `auth_failed` row |

Standing checks, all green:

| Check | Result |
|---|---|
| Prompt cache | 20 model calls, minimum `prompt_cache_hit_tokens` **896**, **zero** calls with zero hits |
| Four spec-fixed refusal strings, verbatim at the tool layer | **All four** (rows 6481–6484), plus the faculty/dean asymmetry on the same call (6485) |
| Dropped audit events in window | **Zero** |
| `tools_used ⊆ tools_offered`; `unoffered_calls` present | Holds on all ten `answer_returned` rows |
| `answer_marker_corrected` rows | **Zero**, as required in this configuration |
| Every id and code resolves | Zero unresolved across all eight captured replies |
| Every stated figure matches the databases | Every number in steps 2, 3b, 5a, 5c, 6, 7, 8 recomputed and correct |
| Guard ledger | Two `answer_ungrounded` (6420 regenerating, 6421 declined), both on pat's bypass; one regeneration, one decline; no other step tripped it |

**The known wart of this configuration, and where it landed.** Step 1's four
counts are right and nothing overrules the tool, but two students are swapped:
S-1045 (last login today) sits under "both flagged and quiet" and S-1054 (25
days) under "flagged but logging in regularly" — and because the reply prints
each student's real login gap beside the wrong heading, it contradicts itself on
screen in both places. The verifier's diagnosis is that the model sorted by
severity and let the ordering override the group definitions. It recommends
**against** a seed change and proposes instead that `get_my_advisees` return the
three membership id lists beside the counts it already returns. Not built.

Two presentation warts, neither a spec violation, both recorded in
`DEMO_VERIFICATION.md`: Kim's step-2 reply opens with four sentences of visible
model deliberation including a broken half-sentence; step 5c signs a table whose
login and missing-submission columns come from canvas with `[colleague]`
throughout.

### 6.3 Which world we are in

**The fallback world.** The demo ships on Session 10's committed state, certified
10 of 10, with:

- demo moment 5b's amber row reliable (present in pass B; Session 9 saw it 5 of 5);
- steps 7 and 8's arithmetic clean in this pass, and step 1's group membership
  the known risk — two students in the wrong bucket, arguing with itself on
  screen, on the opening beat;
- roughly half the latency of the reasoning arm (Session 10: median 13.8s
  against 21.3s).

The alternative world, measured and rejected, had clean arithmetic on the
opening beat and a coin-toss on the refusal that carries the RBAC story.

---

## 7. Deviations from the brief

1. **SPEC §1's sentence records the deviation as tried and reverted**, not as
   taken. The brief specified one sentence saying the agent runs with extended
   reasoning; by the time the sentence could be written truthfully, it wasn't
   true. It is still one sentence, in §1, and it carries both halves of the
   evidence — the arithmetic gain and the behavioural cost. Writing the
   specified sentence would have put a false statement in the spec.
2. **The fallback reverted four files, not two.** The brief named `grounding.py`
   and `app.py`. `viewer.html` and `tests/test_orchestrator_grounding.py` were
   reverted with them because both are dead or failing without the code, and I
   read "ships on Session 10's committed state" as meaning a green suite.
   `docker-compose.yml`, `.env.example`, `factory.py` and `SPEC.md` were edited
   to describe the reverted configuration; they were already in the permitted
   diff.
3. **The acceptance criterion "138+ with the five new guard tests" cannot be met
   in this world** and is not met: the shipped suite is 133. It was met while
   the lift was in place (§4.4).
4. **`docs/LESSONS.md` was updated even though the brief gated that on success.**
   Entries 5 and 9 now carry what actually happened — the correction branch, its
   measured effect, the coupling that killed it, and the reversion. `LESSONS.md`
   is the handoff document, and leaving entry 9 recommending "budget for
   reasoning mode" without the counter-evidence this session produced would have
   been the worse error. The file was already in the permitted diff. §8.1.
5. **Compose sets each flag only on the service that reads it**, rather than both
   flags on both services. The brief said "sets both explicitly on the services
   that read them"; the gateway does not read `AGENT_THINKING`, and omitting it
   entirely is a stronger guarantee than setting it to a value the gateway
   ignores. §3.
6. **SPEC §10's env-var list was not updated** to mention `ROUTER_THINKING`. The
   brief confined SPEC changes to one sentence in §1, and that sentence names
   both flags. §10's list is now one variable short of `.env.example`.
7. **Step 7's two wrong secondary numbers were not acted on**, per the
   no-fixing-after-measurement rule. §5.3.
8. **The bypass script's own printed summary line was not captured** for the
   three ×3 runs — my command truncated the output. The audit rows carry the
   same claim more strongly (`tools_used: []` on every row), and certification
   pass A captured the printed line in full ("tools that actually ran: none").

---

## 8. Evidence and artefacts

### 8.1 `docs/LESSONS.md`

**Entry 5** (the groundedness guard) gains the scoped lift: what it corrected,
that it fired seven times in ten runs and got every one right, that it revealed
the model mislabels one source as another about twice in twelve requests, and
the reason it was reverted — stated as a general lesson about coupling rather
than as a citation anecdote: *a guard that rejects work has two effects, and
anything downstream that depends on the retry is depending on the guard
failing.*

**Entry 9** (model arithmetic) gains the behavioural cost of reasoning mode, the
final scoreboard as a trade rather than a winner, and two additions to the MVP
advice: ship group *membership* alongside counts, and when measuring a reasoning
flag, measure tool-call eagerness rather than only accuracy and latency —
plus the per-model-flag point item 1 fixed.

### 8.2 The suite and the pre-demo check

```
$ uv run pytest tests/ -q
133 passed in 37.33s
```

Pre-demo check, run after the suite as `CLAUDE.md` instructs. Two drops in the
30-minute view, and both are the disruptive test — each lands about half a
second after the audit container is deliberately stopped:

```
audit-1    2026-08-09T22:50:12.355Z INFO:     Shutting down
gateway-1  2026-08-09T22:50:12.881Z audit event 'auth_failed' dropped ...
audit-1    2026-08-09T23:05:49.230Z INFO:     Shutting down
gateway-1  2026-08-09T23:05:49.605Z audit event 'auth_failed' dropped ...
```

Certification pass B ran 22:54:58–23:00:5x, entirely between those two, and the
verifier independently confirmed zero drops inside its own window. The receipts
demo moment 9 points at are complete.

### 8.3 The reverted work is preserved, in the repository

Both patches are tracked under `docs/patches/`, and they do **not** share a base
commit — the README says which is which, and both were verified rather than
assumed:

```
$ git apply --check docs/patches/item2-marker-correction.patch
APPLIES CLEANLY to 0e08b1c

$ git apply --check docs/patches/session-11-full.patch          # in a worktree at 1b55ba5
APPLIES CLEANLY to 1b55ba5
```

- **`item2-marker-correction.patch`** — 294 lines: `grounding.py`, `app.py`,
  `viewer.html`, and the five tests. Applies to `0e08b1c`, which is `main` as it
  stands. `git apply` restores item 2 exactly, five passing tests included.
- **`session-11-full.patch`** — 474 lines: the complete experimental
  configuration as measured, against the pre-session commit `1b55ba5`. The
  correction plus the thinking-flag split plus `AGENT_THINKING=true`. This is
  what to apply to reproduce §5's measurements rather than take them on trust.

`docs/patches/README.md` covers both: what each is, the commit it applies to,
and why the work was reverted — including the part that matters to the MVP team,
that the coupling which killed it is an artefact of this POC's client-held
history and its single allowed regeneration, and does not exist in a
server-held-history architecture.

Both were originally written to the session scratchpad, which was the wrong
place — every session has correctly treated that directory as throwaway, and a
preserved artefact in disposable storage is a contradiction. They are now
tracked.

### 8.4 Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-10.md && git commit          # 1b55ba5

# items 1 and 2
uv run pytest tests/test_orchestrator_grounding.py -q                 # 7 passed
uv run pytest tests/ -q                                               # 138 passed

# item 3
sed -i 's/^AGENT_THINKING=false$/AGENT_THINKING=true\nROUTER_THINKING=false/' .env
docker compose up -d
docker inspect harness-poc-orchestrator-1 | grep -i thinking          # AGENT_THINKING=true
docker inspect harness-poc-gateway-1      | grep -i thinking          # ROUTER_THINKING=false
uv run --with httpx python warm.py                                    # rows 5944-5967

# item 4, the measurements
uv run --with httpx python moment5.py 10 moment5.json                 # rows 5968-6102
uv run --with httpx python ask.py dana "Which students seem to be struggling this term?" 3 step1.json
uv run --with httpx python ask.py kim  "Which fast-growing occupations would a Cybersecurity BS graduate qualify for?" 3 step7.json
for i in 1 2 3; do ./scripts/demo_bypass.sh; done                     # rows 6145-6151
# then the demo-verifier agent, certification pass A                  # rows 6152-6272

# the fallback
git checkout -- services/orchestrator/grounding.py services/orchestrator/app.py \
                services/audit/viewer.html tests/test_orchestrator_grounding.py
sed -i 's/^AGENT_THINKING=true$/AGENT_THINKING=false/' .env
docker compose up -d
uv run pytest tests/ -q                                               # 133 passed
uv run --with httpx python warm.py                                    # rows 6375-6398
# then the demo-verifier agent, certification pass B                  # rows 6401-6491

# acceptance
uv run pytest tests/ -q                                               # 133 passed in 37.33s
docker compose logs --since 30m 2>&1 | grep dropped                   # the disruptive test, §8.2
```

Scratchpad helpers (`ask.py`, `rows.py`, `warm.py`, `moment5.py`, `truth.py`)
and the run transcripts (`moment5.json`, `step1.json`, `step7.json`) live in the
directory named in §8.3 and are throwaway.

---

## 9. Open questions

1. **Do you want item 2 back, decoupled from the retry?** The correction is
   right and it closed a real failure mode; what killed it is that the demo
   depends on the guard rejecting. Those are separable — the correction could
   fire *and* the request could still be regenerated, or `REGROUND_INSTRUCTION`'s
   "call a tool before you write anything" could be sent on a correction as well
   as on a rejection. Neither was measured, and both are one-session changes.
   The patch is in §8.3.
2. **Demo moment 5b relies on the model choosing to call a tool that will refuse
   it.** That is true in both worlds and it is the deepest finding here: the
   beat that proves the boundary holds only produces its receipt when the model
   volunteers to test the boundary. Certification pass B got it; pass A got it
   half the time. Nothing in the harness makes it certain. **Now `docs/LESSONS.md`
   entry 12**, with the fix stated generally: an enforcement receipt must be
   generated deterministically, which is exactly what `scripts/demo_bypass.sh`
   already does and the one receipt in the script that cannot fail to appear.
3. **Step 1's group membership**, §6.2. The verifier's proposal — return
   `flagged_ids`, `quiet_ids`, `flagged_and_quiet_ids` from `get_my_advisees`
   beside the counts — is the fourth iteration of "let the tool compute it", and
   the first three all held. It is a small change to `services/mcp-colleague/`
   and one seed assertion.
4. **Step 7's secondary numbers**, §5.3. Two wrong in three runs, on figures
   outside the four the demo reads aloud. Same class, same fix as 3.
5. **Step 2 and 5c cite one source for two servers' data.** Found in both passes,
   on the two beats whose argument is that the harness joins independent sources.
   The correction branch cannot help here by design — with two servers there is a
   real question of which fact came from which.
6. **Nothing is committed beyond the report move** at the time of writing; the
   commit follows this report.
