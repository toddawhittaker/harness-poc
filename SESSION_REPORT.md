# SESSION_REPORT — harness-poc Session 16

A bounded experiment with a pre-authorized fallback: per-intent reasoning
routing. It was built, it was measured, **it failed one of its acceptance
criteria, and the fallback fired.** The code is reverted on `main`, Session 15's
certificate stands unchanged, and the demonstration ships on it.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

## The headline, in six sentences

**The routing mechanism worked, and the two things everyone expected it to break
did not break.** Across 33 requests and 66 model calls, every `answer_returned`
row carried the budget its intent and role called for, **zero model calls hit a
cold prompt cache**, and demo moment 5's tool-layer refusal fired in **5 of 5
runs** — against roughly half of ten under Session 11's global reasoning flag,
and against the single miss that failed Session 15's certification.

**It closed one of the two characterized residual classes outright.** Step 7 ran
five times with reasoning on and produced **zero wrong intersection tallies**, on
a beat Session 14 measured wrong in 3 of 5 runs. Forty-plus numerators and every
denominator exact.

**It did not close the other, and that is what failed it.** Step 2 stated one
ordinal claim contradicting `missing_per_student` in 1 of 5 runs — "0.55 … the
best rate on that one measure" where IS-MS is lower — and a second run attached
one programme's enrolment and missing count to another programme. The brief's
criterion was *zero* ordinal claims and values 30 of 30. Both clauses failed.

**So the fallback executed exactly as written**: `git checkout` of the session's
code, the stack brought back up, `pytest` green at 141, one spot-check beat
confirming the reverted behaviour. **Nothing was fixed after measurement began
and no beat was re-run.**

**The experiment is preserved rather than thrown away**, on the branch
`session-16-experiment` (commit `8724ee2`), the same judgement `docs/patches/`
records for Session 11. `docs/LESSONS.md` entry 9 carries the measured
before-and-after, as the brief required either way.

**`main` carries one document and this file. Suite green at 141.**

---

## 1. What was done

| Brief item | Status |
|---|---|
| 1 — `agent_model(reasoning: bool \| None = None)`, `router_model()` unchanged, one comment naming the override a budget | **BUILT.** §2.1 |
| 2 — gateway category map gains a reasoning column, forwards `{reasoning: bool}`, fail-open stays cheap, triage-nurse comment preserved with a sibling | **BUILT.** §2.2 |
| 3 — orchestrator accepts the flag, passes it to `agent_model()`, `answer_returned` gains `"reasoning"` | **BUILT.** §2.3 |
| 4 — tests: end-to-end plumbing, and the category→reasoning map unit-tested from the config | **BUILT.** 21 tests, suite 141 → **162**. §2.4 |
| 5 — measure: cache, then residuals, then protected beats, then latency | **MEASURED. The step-2 residual criterion FAILED.** §4 |
| 6 — one certification pass, LESSONS + DEMO_VERIFICATION + the commit | **NOT RUN / NOT DONE.** Conditioned on item 5 holding. §5 |
| FALLBACK — revert, restore, confirm, report | **EXECUTED.** §6 |
| Rule — nothing outside the permitted paths; nothing fixed after measurement; no re-runs | **HELD.** §8 |

Session start: `SESSION_REPORT.md` (Session 15's) was moved to
`reports/session-15.md` and that move was committed by itself as **`8f6dd51`**,
per `CLAUDE.md`.

### 1.1 One decision taken before any code was written, and why it was put to you

The brief's category map does not match the intents the router actually assigns.
I read the intents off Session 15's own certification window before writing the
table:

| Beat | Persona | Router intent |
|---|---|---|
| 1, 2, 2b, 6 | dana, kim, kim, dana | `advisee_detail` |
| 5a, 5b, 5c | noor, noor, kim | `program_aggregate` |
| 3b, 7, 8 | pat, kim, kim | `labor_market` |

There is no curriculum-synthesis intent — steps 7 and 8 come back
`labor_market` — and kim's step-2 question carries the same label as dana's step
1 and step 6. Keyed on category alone, the brief's map is not satisfiable:
`advisee_detail → false` makes step 2 non-reasoning, so item 5's central
measurement cannot be run; `program_aggregate → true` puts noor's moment-5 turns
on the exact path Session 11 measured as costing the refusal.

I stopped and asked rather than guessing, because the alternative readings led to
materially different experiments. You chose a `(category, role)` key and amended
it. The table below is what you specified, verbatim in intent:

```python
REASONING_BY_CATEGORY: dict[tuple[str, str], bool] = {
    ("advisee_detail", "advisor"): False,     # dana, moments 1 and 6
    ("advisee_detail", "dean"): True,         # kim, moment 2 — the synthesis shape
    ("program_aggregate", "dean"): True,      # kim, moment 5c — the rollup
    ("program_aggregate", "faculty"): False,  # noor, moment 5 — protected
    ("labor_market", "dean"): True,           # kim, moments 7 and 8
}
REASONING_DEFAULT = False   # 'other', unknown pairs, and the fail-open path
```

`labor_market` is dean-keyed rather than blanket-true, so pat's twelve-row lookup
is not taxed fifteen seconds for nothing. A caller holding several roles gets the
budget if any of their pairs asks for it. Every `True` cell is a dean synthesis
beat.

---

## 2. What was built

The whole diff is on branch **`session-16-experiment`**, commit **`8724ee2`**,
four files, 181 lines of diff plus a 300-line test file. `git diff main
session-16-experiment` shows it in full. Summary:

### 2.1 `libs/harness_models` — the override

```python
def agent_model(reasoning: bool | None = None) -> OpenAIChatModel:
    """The orchestrator's execution model (SPEC §4.3).

    `reasoning` overrides AGENT_THINKING for this one call: None takes the env
    default, True or False sets the budget for this request and no other. …

    The override is a latency/quality budget, never a security property: no
    authorization decision anywhere reads it, and every enforcement layer
    below behaves identically whichever way it is set.
    """
    return _model(
        AGENT_MODEL, AGENT_SETTINGS if reasoning is None else _settings(reasoning)
    )
```

`router_model()` was not touched. `AGENT_SETTINGS` is never mutated — the
override builds a fresh settings object, so one request cannot change the next.

### 2.2 gateway

The table in §1.1, `reasoning_for(intent, roles)`, and `"reasoning": reasoning`
added to the JSON posted to the orchestrator. The mandated comment is preserved
byte-for-byte with one sibling line beneath it:

```
# The router is a triage nurse, not a judge. Enforcement lives in the MCP servers. Do not add authorization logic here.
# The reasoning hint the triage assigns below is a spending decision, not a verdict: the enforcement beneath neither reads it nor trusts it.
```

The fail-open path needs no special case: `FAIL_OPEN.intent` is `"unclassified"`,
which is absent from the table, so a router that could not speak buys nothing.
The role key carries a long comment saying it is a budget and not an entitlement,
that every cell flipped either way returns the same data to the same people, and
that an MVP splits the intents and drops the role.

### 2.3 orchestrator

`ChatRequest.reasoning: bool | None = None`, resolved once at the top of `/chat`
so the model that runs and the receipt that records it cannot disagree:

```python
reasoning = AGENT_THINKING if request.reasoning is None else request.reasoning
...
agent = Agent(agent_model(reasoning), instructions=SYSTEM_PROMPT, toolsets=…)
```

`answer_returned` gained `"reasoning": reasoning`. Nothing else changed —
`REGROUND_INSTRUCTION`, the prompts and `grounding.py` were not touched.

**The bypass is unchanged by construction.** `scripts/demo_bypass.sh` skips the
gateway and sends no such field, so it takes `AGENT_THINKING` exactly as before.
That is stated in the code comment and was confirmed by test and by two live
bypass runs.

### 2.4 tests — `tests/test_reasoning_routing.py`, 21 tests

Suite went **141 → 162** (acceptance asked for 145+). No existing test was
touched, weakened or removed.

The factory and the gateway table are lifted from the shipped source and compiled
against stubs — the technique `tests/test_orchestrator_receipts.py` already uses,
because this workspace deliberately carries no pydantic, pydantic-ai or fastapi.
An edit to either file changes what runs.

- **The override is per request**: `agent_model(True)` and `(False)` send the
  right `thinking` body; `agent_model()` and `(None)` take the env default; the
  module-level settings object is asserted unmutated afterwards.
- **`router_model()` still takes no argument** — asserted from its signature.
- **Every demo beat, parameterized** by the intent the router really assigns it,
  eleven cases, plus the protected cell asserted on its own with Session 11's
  measurement quoted in the failure message.
- **Fail-open, `other`, an improvised intent, and a caller with no roles** all
  resolve to `False`; a two-role caller gets the budget in either order.
- **Three live tests** post straight at the orchestrator and read the row back:
  `reasoning: true` and `false` land on the receipt, and a request with no field
  inherits `AGENT_THINKING`.

One bug in my own tests, found and fixed **before the measurement window opened**:
the live tests originally drove pat, and `tests/test_skills.py` polls for pat's
newest `answer_returned` row within a two-second slack. On the first full-suite
run that test picked up my row instead of its own and failed. The fix was to
drive sam — a persona no other live test uses — and to identify the row by an
audit-id watermark rather than by timestamp, since audit timestamps are written
to whole seconds. That is a test-isolation defect I introduced, not a flake.

---

## 3. Build verification, before the window opened

Gateway and orchestrator restarted, then one kim request and one two-turn noor
request. **Audit rows 8921–8939, 02:58:05–02:58:44Z.**

```
8921 router      kim   intent=advisee_detail     hit=896 miss=56
8927 answer      kim   reasoning=True   lat=24908.1 hit=6912 compl=1614
8928 router      noor  intent=program_aggregate  hit=896 miss=59
8934 answer      noor  reasoning=False  lat=6852.7  hit=8704 compl=230
8935 router      noor  intent=program_aggregate  hit=896 miss=56
8936 tool_call   noor  mcp-canvas  get_section_engagement decision=refused
8938 answer      noor  reasoning=False  lat=4116.9  hit=5376 compl=94
```

The table fires, the flag reaches the receipt, and noor's second turn reached the
tool server and was refused. Nothing was changed after this point except by the
fallback.

---

## 4. The measurement

All personas warmed after the restart with an off-script question — **rows
8940–8964, excluded from scoring.** The measurement is **rows 8965–9230, 266
rows, 02:59:44–03:10:17Z**, driven through the gateway's `/chat` with real RS256
persona tokens, one fresh conversation per run (empty history every time).

### 4.1 Cache — PASS

Run first, as the brief ordered, because a per-request `thinking` setting
breaking DeepSeek's prefix cache would have been an immediate fallback.

| Window | Rows | Mode | Model calls | Zero-hit | Min hit tokens |
|---|---|---|---|---|---|
| step 2 ×2 (kim) | 8965–8978 | reasoning | 4 | **0** | 896 |
| step 1 ×2 (dana) | 8979–8988 | cheap | 4 | **0** | 896 |

Identical questions returned identical hit counts in each mode — 6656 on both
reasoning answers, 5888 on both cheap ones — which is the signature of an
unchanged prefix. **Across the whole measurement: 66 model calls with telemetry,
zero zero-hit, minimum 896.** Per-request thinking settings do not disturb the
prompt cache.

### 4.2 The residuals — step 7 PASS, step 2 **FAIL**

Ground truth was recomputed from `data/*.db` read-only for every figure below,
not quoted from an earlier report. It had not drifted from Session 14's.

#### Step 7 ×5, reasoning on — rows 9024–9089 — **PASS, 5 of 5**

Criterion: *zero intersection tallies contradicting their own covered/missing
lists, denominators still matching `skill_count`.*

**Met completely.** Every occupation figure in all five runs was exact: every
numerator, every `skill_count` denominator, every growth percentage, every median
wage, every covered-skill list, every missing-skill list, both SOC codes where
runs printed them. Run 3 listed all eight non-zero occupations with their covered
and missing skills spelled out and every one was right.

| Occupation | Truth | Runs stating it | Wrong |
|---|---|---|---|
| Information Security Analysts | 8 of 8 | 5 | 0 |
| Cloud Infrastructure Architects | 3 of 7 | 5 | 0 |
| Network and Computer Systems Administrators | 3 of 6 | 5 | 0 |
| Software Developers | 2 of 6 | 5 | 0 |
| Computer Systems Analysts | 2 of 5 | 4 | 0 |
| Computer and Information Systems Managers | 1 of 5 | 5 | 0 |
| Medical and Health Services Managers | 1 of 5 | 3 | 0 |
| Medical Records Specialists | 1 of 5 | 2 | 0 |
| AI/ML, Data Scientists, Management Analysts, Financial Analysts | 0 of 7/7/5/6 | 3 | 0 |

**Session 14 measured this beat wrong in 3 of 5 runs.** Run 5 also stated a
correct ordinal — "at 32.7% projected growth it is the third-fastest-growing
occupation on the list" — which is right.

Two presentation warts, both familiar: runs 2 and 5 promised an ordering
("ordered by growth") and then broke it in the table beneath.

#### Step 2 ×5, reasoning on — rows 8989–9023 — **FAIL**

Criterion: *zero ordinal claims contradicting `missing_per_student`, values still
30/30.* Ground truth:

```
prog   sections enroll pct_active missing missing_per_student
BUS-BS        4     22      63.6       12   0.545
CS-BS         3     20      95.0       16   0.800
CYB-BS        5     43      86.0       28   0.651
DAT-MS        3     29      89.7       24   0.828
HIM-BS        3     31      77.4       22   0.710
IS-MS         2     20      80.0       10   0.500
TOTAL        20    165         —      112

burden rank: DAT-MS > CS-BS > HIM-BS > CYB-BS > BUS-BS > IS-MS
```

**Failure 1 — run 1 (row 8995), an ordinal claim contradicting the field.**

> Missing submissions per student are 0.55, which is **the best rate on that one
> measure**, but that low number sits beside the weakest login and GPA figures …

BUS-BS at 0.545 is second-best; IS-MS at 0.500 is best. This is the same error in
the same words that Session 14 recorded at run 4 without reasoning.

**Failure 2 — run 2 (row 9002), a wrong tool-stated value.**

> **DAT-MS** … leads in immediate missing-work burden at **0.83 missing
> submissions per student** this week [colleague]. **28 of 43 enrolled students
> are affected**, even though 89.7% logged in …

DAT-MS is 24 missing across 29 enrolled. 28 and 43 are **CYB-BS's** figures,
attached to DAT-MS. Both numbers come straight from a tool result, so this is a
tier-(a) error under Session 15's rubric — the class reasoning is least expected
to leave behind.

**Runs 3, 4 and 5 are clean on every figure and every ordinal**, and each states
the BUS-BS rank correctly ("the second-lowest missing-submission burden",
"the second-lowest burden") — the very claim run 1 got wrong.

Every `missing_per_student` value stated was exact: **24 of 24** across the five
runs (runs print between three and six of the six programmes; the brief's "30/30"
assumed all six every time).

One borderline finding recorded and not scored: run 1 says three programmes have
"GPA averages above 3.10" where CS-BS is exactly 3.10.

**Verdict: 1 wrong ordinal in 5 runs against Session 14's 2 in 5, and one wrong
tool-stated value that Session 14 did not have. The criterion said zero. FAILED.**

#### Step 8 ×2, reasoning on — rows 9090–9124 — regression check

Both runs surfaced AI/ML Engineers and Cloud Infrastructure Architects as the
unmapped fast-growers, both called `get_course_outcomes` across the catalog
before any catalog-wide claim, and every per-programme coverage figure in both
runs was exact — including run 2's eight "already fully covered" pairings, all
eight correct.

Run 2 carries one self-contradiction of the step-7 class: **"Two skills — deep
learning, containerization, and infrastructure automation — are taught by no
program"** names three skills after saying two. The three skills are the right
three.

### 4.3 The protected beats — PASS, all of them

| Beat | Runs | Mode on the row | Result |
|---|---|---|---|
| moment 5, both turns | ×5, rows 9125–9189 | `reasoning=False` on all 10 | **5 of 5 reached the tool server and relayed the refusal.** Zero declines |
| step 1 | ×3, rows 9190–9204 (and ×2 in the cache window) | `reasoning=False` | 25 advisees / 9 flagged / 6 flagged-and-quiet in every run; students, GPAs, login gaps exact |
| moment 6 | ×2, rows 9205–9220 | `reasoning=False` | Leon Cline S-1055 CS-BS GPA 3.41; three open courses with seats; CS-460 correctly blocked; prior grades and terms exact |
| step 3b | ×2, rows 9221–9230 | `reasoning=False` | All twelve growth rates, wages and SOC codes exact, correctly ranked; ~8s, unchanged |
| bypass | ×2 | no flag sent | mcp-colleague refused verbatim both times, amber both times |

**Moment 5 is the result worth reading twice.** All six `get_section_engagement`
refusal rows in the window carry the spec-fixed sentence verbatim:

```
9133 refused  Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean.
9135 refused  (same)
9147 refused  (same)
9161 refused  (same)
9174 refused  (same)
9186 refused  (same)
```

Five runs, five refusals reaching the tool layer, against Session 11's roughly
half of ten under a global reasoning flag and against Session 15's certification,
which lost this beat outright. Routing the budget away from this beat protected
it — which is the half of the experiment that worked.

### 4.4 Latency — medians per beat per mode

From the `answer_returned` rows, seconds:

| Beat | Mode | Session 16 median | Session 14 (no reasoning) |
|---|---|---|---|
| step 2 ×5 | reasoning | **22.6** | 17.9 |
| step 7 ×5 | reasoning | **28.3** | 17.3 |
| step 8 ×2 | reasoning | **44.6** (30.4 and 62.3) | — |
| step 1 ×3 | cheap | 10.0 | — |
| moment 5 ×5 (10 turns) | cheap | 6.4 | — |
| moment 6 ×2 | cheap | 7.4 | — |
| step 3b ×2 | cheap | 6.5 | — |

The synthesis beats running around twenty seconds was accepted by prior ruling.
**Step 8's 62-second run was not**, and it is worth flagging: it is the longest
single beat in the record and it happened on the beat the room is told is
programme strategy.

### 4.5 Standing checks over the measurement window

```
window rows 8965-9230 (266 rows)
model calls with telemetry: 66   zero-hit: 0   min hit: 896
answer_returned: 33   declines: 0   regenerations: 2
rows violating tools_used ⊆ tools_offered: none
rows missing the reasoning key: none
amber (refused) tool rows: 9133 9135 9147 9161 9174 9186
Counter({'tool_call': 165, 'router_classified': 33, 'request_completed': 33,
         'answer_returned': 33, 'answer_ungrounded': 2})
```

Every `answer_returned` row carried the correct flag for its intent and role —
33 rows, no exceptions, no missing keys:

```
dana  advisee_detail     reasoning=False  x7
kim   advisee_detail     reasoning=True   x7
kim   labor_market       reasoning=True   x7
noor  advisee_detail     reasoning=False  x1
noor  program_aggregate  reasoning=False  x9
pat   labor_market       reasoning=False  x2
```

The audit viewer needed no change: `reasoning` renders inside the detail column
like every other detail key.

---

## 5. Item 6 was not run

The brief conditions the certification on *"If all of item 5 holds"*. It does
not. Session 14 set the precedent and this session follows it: the certification
was not run, `DEMO_VERIFICATION.md` was not touched, and Session 15's certificate
remains the current record without amendment.

---

## 6. The fallback, executed

> **FALLBACK, pre-authorized, no round trip:** on any item-5 failure … `git
> checkout` the session's code changes, `docker compose up -d`, confirm pytest
> green and one spot-check beat, and report.

1. **The experiment was committed to a branch first**, so a measured result is
   not destroyed by its own reversion — `session-16-experiment`, commit
   `8724ee2`, the same judgement `docs/patches/README.md` records for Session 11.
   `main`'s working tree was then returned to Session 15's code.

   ```
   $ git checkout main && git status --porcelain
   (empty)
   $ git diff --exit-code --stat services/ libs/ tests/ config/ apps/ scripts/
   UNCHANGED
   ```

2. **The stack was restored** — `docker compose up -d`, then gateway and
   orchestrator restarted so the reverted code is what is running. All ten
   containers healthy.

3. **Suite green, back at Session 15's number:**

   ```
   $ uv run pytest tests/ -q
   141 passed in 49.61s
   ```

4. **Spot check — moment 5, both turns, rows 9351–9365, 03:16:35Z:**

   ```
   9360 answer_returned noor  "reasoning" key present: False  hit=10624
   9362 tool_call mcp-canvas get_section_engagement decision=refused
        Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean.
   9365 answer_returned noor  "reasoning" key present: False  hit=5504
   ```

   The key is gone from the receipt, the refusal still fires, the cache still
   hits. The revert is complete and the behaviour is Session 15's.

**No fix was made after measurement began. No beat was re-run.** The step-2
failure is a model behaviour and closing it would have required a code change
after the fact, which is the one thing the rules forbid.

---

## 7. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | `agent_model(reasoning)` with `None` = env default; `router_model()` unchanged; the budget-not-security comment | **PASS.** §2.1 |
| 2 | Gateway reasoning column, config-driven; `{reasoning}` forwarded; fail-open cheap; triage comment preserved plus a sibling | **PASS**, with the `(category, role)` key you approved. §1.1, §2.2 |
| 3 | Orchestrator accepts the flag, passes it to `agent_model()`, `answer_returned` gains `"reasoning"`; nothing else changed | **PASS.** §2.3 |
| 4 | Tests: end-to-end plumbing, and the map unit-tested from the config | **PASS.** 21 tests. §2.4 |
| 5a | Cache: step 2 ×2 and step 1 ×2, zero zero-hit in both modes | **PASS.** 0 of 66 calls cold. §4.1 |
| 5b | Step 2 ×5: zero ordinal claims contradicting `missing_per_student`, values 30/30 | **FAIL — 1 wrong ordinal, 1 wrong tool-stated value.** §4.2 |
| 5c | Step 7 ×5: zero contradicting tallies, denominators matching `skill_count` | **PASS — 5 of 5 clean.** §4.2 |
| 5d | Step 8 ×2: regression | **PASS on figures**; one self-contradicting count in run 2. §4.2 |
| 5e | Moment 5 both turns ×5: relayed refusal with amber row at Session 15's rate or better, zero declines | **PASS — 5 of 5, zero declines.** Better than Session 15. §4.3 |
| 5f | Step 1 ×3 and moment 6 ×2: non-reasoning on the rows, behaviour unchanged; bypass ×2 | **PASS.** §4.3 |
| 5g | Step 3b ×2 as pat (your addendum): `reasoning=false`, unchanged | **PASS.** §4.3 |
| 5h | Latency medians per beat per mode; all personas warmed; every window labelled | **PASS.** §4.4, §4 |
| 6 | Certification, DEMO_VERIFICATION, LESSONS closing paragraph, the commit | **NOT RUN.** Conditioned on item 5. §5 |
| — | LESSONS entry 9 gets the evidence either way | **DONE.** §9 |
| — | FALLBACK on any item-5 failure | **EXECUTED as written.** §6 |
| — | `pytest` green, 145+ with the new tests | **PASS — 162** with the experiment; **141** after the revert. §2.4, §6 |
| — | Diff confined to the permitted paths | **PASS.** §8 |
| — | Nothing fixed after measurement began; no re-runs | **HELD.** §6 |

---

## 8. Evidence — the diff, and what was never touched

`main`'s diff after the fallback is one document plus this file:

```
$ git status --porcelain
 M docs/LESSONS.md
?? SESSION_REPORT.md

$ git diff --stat
 docs/LESSONS.md | 55 +++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 55 insertions(+)
```

`DEMO_VERIFICATION.md` is **not** in that list, and that is deliberate: item 6
never became due, so Session 15's certificate stands in it untouched and
unamended.

The experiment's own diff, on the branch, touched exactly four paths, all
permitted: `libs/harness_models/src/harness_models/factory.py`,
`services/gateway/app.py`, `services/orchestrator/app.py`, and
`tests/test_reasoning_routing.py`. **Nothing in `services/audit/`, any `mcp-*`
service, either `prompts.py`, `grounding.py`, `config/skills.yaml`, `apps/` or
`scripts/` was touched at any point in the session** — proven, not asserted:

```
$ git diff main session-16-experiment --stat
 libs/harness_models/src/harness_models/factory.py |  18 +-
 services/gateway/app.py                           |  60 +++-
 services/orchestrator/app.py                      |  21 +-
 tests/test_reasoning_routing.py                   | 300 ++++++++++++++++++
```

The pre-demo check, run after the suite as `CLAUDE.md` instructs:

```
$ docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
clean
```

**Zero dropped audit events**, so no row any of the above depends on was lost.

### Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-15.md && git commit          # 8f6dd51

# build, then the suite with the experiment in place
docker compose restart gateway orchestrator
uv run pytest tests/ -q                                               # 162 passed

# build verification, before the window                               # rows 8921-8939
# warm every persona after the restart                                # rows 8940-8964

# the measurement — one fresh conversation per run, toggle off        # rows 8965-9230
uv run --with httpx python ask.py kim  "<step 2>"  2  cache-step2.json
uv run --with httpx python ask.py dana "<step 1>"  2  cache-step1.json
uv run --with httpx python ask.py kim  "<step 2>"  5  res-step2.json
uv run --with httpx python ask.py kim  "<step 7>"  5  res-step7.json
uv run --with httpx python ask.py kim  "<step 8>"  2  res-step8.json
uv run --with httpx python ask.py noor "<5a>" 5 prot-moment5.json --second-turn "<5b>"
uv run --with httpx python ask.py dana "<step 1>"  3  prot-step1.json
uv run --with httpx python ask.py dana "<moment 6>" 2 prot-moment6.json
uv run --with httpx python ask.py pat  "<step 3b>" 2  prot-step3b.json
./scripts/demo_bypass.sh   # twice

# ground truth, recomputed from the databases read-only
uv run python   # the joins printed in §4.2

# the fallback
git checkout -b session-16-experiment && git commit                   # 8724ee2
git checkout main
docker compose up -d && docker compose restart gateway orchestrator
uv run pytest tests/ -q                                               # 141 passed
uv run --with httpx python ask.py noor "<5a>" 1 spotcheck.json --second-turn "<5b>"
docker compose logs --since 30m 2>&1 | grep dropped                   # clean
```

The driver (`ask.py`), the audit reader (`check.py`) and every run transcript are
in the session scratchpad and are throwaway; nothing in the repository depends on
them. `ask.py` posts to the gateway with a real persona token and sends an empty
`history` on every run, so each run is a fresh conversation.

---

## 9. The document that did change

**`docs/LESSONS.md` entry 9** gains a closing subsection, as the brief required
regardless of outcome. It records: that the per-workload routing this entry had
recommended for five sessions was finally built; that it costs nothing in prompt
cache and that moment 5 survived it 5 of 5; the measured before-and-after on both
residual classes side by side (intersections 3-of-5 wrong → 0 of 5; ordinals
2-of-5 wrong → 1 of 5); that it failed its acceptance and was reverted, with the
branch named; and the advice that falls out — route the budget per intent,
expect it to close set-intersection arithmetic and expect it not to close ordinal
claims, and split the intents so the table needs no role key.

---

## 10. Open questions

1. **The ordinal residual now has three failed remedies, not two.** A payload
   field moved it (Session 14), prompt instructions never held it (entry 4), and
   a reasoning budget aimed straight at it reduced it from 2-in-5 to 1-in-5 —
   which five runs cannot distinguish from noise. It is the last open defect in
   the build and the honest position is the one `DEMO_VERIFICATION.md`'s
   presenter section already takes: the values are the tools', the rankings are
   the model's, and the table beside the claim is exact.

2. **Was one bad draw allowed to sink a working mechanism?** Reasonable people
   could disagree, and the report should say so plainly rather than hide it.
   Everything except one clause of one criterion passed, and two of the passes —
   step 7 going to zero, moment 5 going to 5 of 5 — are the best results either
   beat has ever produced. But the criterion was written before the measurement
   precisely so that this decision would not be mine to make afterwards, and
   run 2's "28 of 43" is a wrong tool-stated figure, which is a worse finding
   than the ordinal it accompanied. The fallback was right to fire. **If you want
   the experiment reconsidered, the branch is one `git merge` away and the
   evidence for and against is all in §4.**

3. **Step 8 took 62 seconds once.** Under reasoning, on the beat that closes the
   synthesis story. Nobody has measured its spread, and a demo beat with an
   unmeasured minute-long tail is a risk worth knowing about before it is ever
   routed to reasoning again.

4. **The router taxonomy is the real constraint.** Four categories cannot express
   which beats deserve a budget, which is why the table needed a role key at all.
   That was worked around here; in an MVP it should be fixed at the source, and
   entry 9 now says so.

5. **Everything is committed.** `main` carries the archive move `8f6dd51` and the
   commit following this report; the experiment is on `session-16-experiment` at
   `8724ee2`. Nothing is left uncommitted and nothing else was reverted.
