# SESSION_REPORT — harness-poc Session 9

Five changes, then one measurement pass, and nothing fixed once measurement
began. This report stands alone: it quotes the commands run and their output,
because the person reading it has no access to the terminal it was written from.

**Headline: the receipts are honest now.** Session 8's only regression — pat's
bypass row naming a tool that was never dialled — is closed at the mechanism
rather than at the prompt. `tools_used` means EXECUTED on every row, an attempt
on a tool the caller does not hold gets its own grey `unoffered` row, and I
proved the new path fires live rather than only in a test. The bypass beat ran
ten times with **10 of 10 clean receipts and zero phantom calls**, and a
deliberate probe made the phantom happen on purpose three times out of three
(rows 5082, 5084, 5085). The demo-verifier returned **10 of 10 for the third
session running**. `uv run pytest tests/ -q` reports **133 passed** (130 before).

**Two of the five changes did not buy what they were meant to buy, and both are
the same kind of failure: the model's arithmetic, not the data.**

- **`flagged_and_quiet_count` did not close demo moment 1's opening sentence.**
  The tool now ships the number; across four runs the sentence was right twice,
  wrong once (stated 9 where the tool said 8), and right-then-argued-with once —
  that fourth run quoted the field and then overruled it in the reply: *"The
  server reported 8 flagged-and-quiet, but the data shows 9 individuals matching
  both criteria."* §4.3.
- **Step 7's first partial is now the tally the model gets wrong.** Cloud
  Infrastructure Architects landed at **3 of 7 in 3 of 3 runs**, which is exactly
  what item 5 was for. But Network and Computer Systems Administrators — the
  number that was supposed to hold still at 3 of 6 — was stated as **"4 of 6" in
  2 of 3 runs**, in one case naming three covered skills on the same line. The
  ground truth is unchanged and asserted in the seed; the model miscounts it.
  I cannot rule out that my own edit caused this, and §7.1 says why.

**One ruling changed the shape of item 5.** The brief said to add "cloud
architecture" to a CYB-BS outcome and separately required step 7 to read 3/6 for
the first partial. Those two cannot both hold: "cloud architecture" is one of
Network and Computer Systems Administrators' six skills, so adding it moves that
partial to 4 of 6. You ruled at the outset: keep the measurement line, add **"API
design"** instead, and assert its overlap profile so the choice cannot silently
rot. That is what was built. §2.5.

---

## 1. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | Item 1: `tools_used` means executed; unoffered attempts get their own audit row and an `unoffered_calls` list; bypass script summary updated; test with a phantom `ToolCallPart` | **PASS** — and proven live, not only in the test. §2.1, §4.1 |
| 2 | Item 2: held-by-you qualifier on the two named tools; `SYSTEM_PROMPT` one static literal, AST-verified | **PASS** — one paragraph edited, AST says STATIC, 8431 chars. §2.2, §6.1 |
| 3 | Item 3: `answer_ungrounded` classifies as the grey error class; viewer harness re-run; chip counts reflect it | **PASS** — one line in `rowClass`, 24 of 24 harness checks, error chip went from 11 rows to 13 as the guard fired. §2.3, §4.6 |
| 4 | Item 4: `flagged_and_quiet_count`, docstring, one test, one seed assertion pinned at 8 | **PASS as built** — field, test and assertion all in place and green. **The demo sentence it was for is not fixed.** §2.4, §4.3 |
| 5 | Item 5: second partial becomes 3 of 7; verify() gains the absent-trio, 8/8, 0/7, casting and flagged-and-quiet assertions | **PASS, with the skill changed by your ruling** — 3 of 7 in 3 of 3 runs, every assertion green on the first re-seed. §2.5, §4.4 |
| 6 | Measurement in the stated order, nothing fixed once it began | **PASS** — six windows then the verifier; every finding below is recorded and untouched. §4, §7 |
| 7 | `pytest` green, 133+ | **PASS** — 133 passed in 38.85s. §6.2 |
| 8 | Verifier 10/10 sustained | **PASS** — ten of ten, third session running. §5 |
| 9 | Diff confined to the named files | **PASS** — eight modified files and one new test file, all inside the permitted list. §3 |

---

## 2. What was done

Session start: `SESSION_REPORT.md` was moved to `reports/session-8.md` and that
move was committed by itself as **`8da3262`**, per `CLAUDE.md`. It is the only
commit made this session.

### 2.1 Item 1 — a receipt that can only name tools that ran

`services/orchestrator/app.py`. `tools_called` still reads every `ToolCallPart`
out of the run, and its docstring now says what it is: what the model *asked
for*. One new function does the separating:

```python
def executed_and_unoffered(called: list[str], allowed: set[str]) -> tuple[list[str], list[str]]:
    return ([name for name in called if name in allowed],
            [name for name in called if name not in allowed])
```

Four things read it:

- `tools_used` in the `answer_returned` audit detail and in the `/chat` response
  body is now the executed list, so **`tools_used ⊆ tools_offered` holds on every
  row by construction**;
- `answer_returned` gains `unoffered_calls`, normally empty;
- each unoffered attempt gets its own `tool_call` row, `via: "orchestrator"`,
  `decision: "unoffered"` — no MCP row will ever sit beside it, because nothing
  was dialled;
- **the groundedness guard is now judged against the executed list too.** This
  is one step past the brief's letter and I think it is the brief's intent: a
  phantom call to `get_my_sections` would otherwise put "canvas" in the set of
  servers the guard believes answered, and a marker that cites a server which
  never ran is the exact thing the guard exists to catch. `grounding.py` is
  untouched; only what app.py passes it changed.

`ChatReply` gained `unoffered_calls` so the bypass script can tell the two apart
without reading the audit API. `scripts/demo_bypass.sh` now prints:

```
    tools that actually ran: none
```

and, only when there is something to say, a second line naming what was
attempted and stating that no server was dialled. The old line said "tools the
model actually called", which was the false half of Session 8's contradiction.

### 2.2 Item 2 — the qualifier

`services/orchestrator/prompts.py`, one paragraph, nothing else:

> If you need that list again, call the tool again — get_my_sections for your
> sections **or** get_my_advisees for your advisees, **when you hold them; when
> you hold neither, the answer is what your own tools can show.**

The names stay. The instruction no longer reaches into callers who hold neither
tool, which is the population Session 8 §7.1 suspected of the phantom call.

### 2.3 Item 3 — the guard's own rows are selectable

`services/audit/viewer.html`, one classification line inside `rowClass`, with the
comment that explains it:

```js
if (ev.event === "answer_ungrounded") return "error";
```

`answer_ungrounded` carries no `decision`, so it fell through to green and hid
among the successes — the most interesting row in a run, invisible. It is not a
success and it is not a refusal. Nothing else in `services/audit/` was touched.

### 2.4 Item 4 — the intersection, counted by the tool

`services/mcp-colleague/app.py`. `AdviseeRoster` gained one field beside the
three it already had, computed from the very rows the result ships:

```python
flagged_and_quiet_count=sum(
    1 for a in advisees
    if a.term_grade_flags and a.last_login_days > QUIET_AFTER_DAYS),
```

The tool docstring — which the model reads — now ends "…flagged_and_quiet_count
is how many are both flagged and quiet." Live over MCP with dana's token
(verifier row 5179): `advisee_count 25, flagged_count 9, quiet_count 8,
flagged_and_quiet_count 8`.

### 2.5 Item 5 — the second partial, and the skill that had to change

`scripts/seed.py`. **CYB-410 Security Architecture gained the outcome skill "API
design"**, not "cloud architecture".

The arithmetic behind the swap, computed before any edit:

```
CYB-BS vs Cloud Infrastructure Architects          2/7   missing API design, cloud architecture,
                                                         containerization, distributed systems,
                                                         infrastructure automation
CYB-BS vs Network and Computer Systems Admins      3/6   missing cloud architecture,
                                                         containerization, infrastructure automation
```

"cloud architecture" appears in **both** occupations' skill lists, so adding it
would have lifted the second partial to 3 of 7 and the first to 4 of 6 in the
same stroke — and the brief's measurement line requires the first to stay at 3 of
6. "API design" appears in Cloud Infrastructure Architects and in no other
occupation the demo question reaches, so it moves one number and one number only.
It reads naturally in a security architecture course, which is where it went. You
ruled this at the start of the session; the reasoning is written into the seed
beside the edit so the next person does not undo it.

`verify()` gained five assertions, all green on the first re-seed:

- **the four step-7 tallies exactly** — 8/8, 3/6, 3/7, 0/7 — rather than by shape.
  "Strong, partial, miss" was true before and after; a membership test cannot
  tell you the second partial moved, or that the first one did not;
- **the API-design overlap profile** — present in CYB-BS and in Cloud
  Infrastructure Architects, absent from Information Security Analysts, Network
  and Computer Systems Administrators, and Data Scientists, so this edit can
  never silently move the 8/8, the 3/6 or the 0/7;
- **the catalog-wide absent set is exactly** `{containerization, deep learning,
  infrastructure automation}` — exact in both directions, because a fourth
  untaught skill would be a gap the demo does not know about;
- **flagged-and-quiet is 8**, beside the existing 25 and 9;
- and every casting invariant the brief named was already asserted and still is.

The absent trio was verified unchanged **before** the edit as well:

```
$ python3 -   # taught_skills() over CURRICULUM, before any change
in SKILLS but taught nowhere: ['containerization', 'deep learning', 'infrastructure automation']
```

`uv run scripts/seed.py`, first attempt, nothing retuned:

```
verified:
  dana advises 25, of whom 9 carry a term grade flag and 8 have not logged in for >10 days
    both flagged and quiet: 8
  program spread: GPA 0.36, quiet share 22.7 points
  demo moment 6 asks about S-1055 (Leon Cline, CS-BS)
    taking now: CS-210
    next term:  CS-310, CS-350, CS-410
    blocked:    CS-460
  S-1042 keeps his own answer: nothing new next term, 1 blocked
  noor teaches CYB-310-A, CYB-210-A and no BUS section
  CYB-BS vs Information Security Analysts: 8/8 skills (strong)
  CYB-BS vs Network/Systems Administrators: 3/6 (partial)
  CYB-BS vs Cloud Infrastructure Architects: 3/7 (partial)
  CYB-BS vs Data Scientists: 0/7 (miss)
  unmapped fast-growers: AI/ML Engineers, Cloud Infrastructure Architects
  skills no program teaches: containerization, deep learning, infrastructure automation
```

`data/*.db` were regenerated and the four MCP servers restarted, per `CLAUDE.md`.

### 2.6 Tests

**`tests/test_orchestrator_receipts.py`**, new, 146 lines, two tests. The
functions are lifted out of the parsed source of `services/orchestrator/app.py`
and compiled on their own, against a stub `ToolCallPart` — the same technique and
the same reason as `test_orchestrator_grounding.py` loading `grounding.py`
directly: importing that module would pull fastapi, pydantic-ai and
harness_auth, which this workspace deliberately does not carry. An edit to app.py
changes what runs here; a transcribed copy is what a test of this kind must never
be.

- `test_a_phantom_tool_call_is_not_reported_as_a_tool_that_ran` — a mocked run
  with two labor calls and one `get_my_sections` (Session 8 §7.1 in miniature):
  `tools_used` excludes it and is a subset of the offered set, `unoffered_calls`
  names it, and the deduplicated call order is checked too.
- `test_an_ordinary_run_reports_no_unoffered_calls` — empty on a normal run and
  on a run that called nothing, because a field that is only ever populated is a
  field nobody trusts when it is empty.

**`tests/test_tool_results.py`**, +30 lines, one test —
`test_the_advisee_roster_counts_the_students_who_are_both`: the field is present,
equals the size of the intersection computed from the shipped rows, and is
greater than zero. Matches the file's one-test-per-count convention.

---

## 3. The diff

```
 DEMO_VERIFICATION.md             | 848 ++++++++++++++++++++++++++++++++++++++-
 scripts/demo_bypass.sh           |  10 +-
 scripts/seed.py                  |  84 +++-
 services/audit/viewer.html       |   4 +
 services/mcp-colleague/app.py    |  15 +-
 services/orchestrator/app.py     |  68 +++-
 services/orchestrator/prompts.py |   7 +-
 tests/test_tool_results.py       |  30 ++
 8 files changed, 1049 insertions(+), 17 deletions(-)

 tests/test_orchestrator_receipts.py   | new file, 146 lines
```

Plus this file, and the regenerated `data/*.db` (gitignored). Every path is
inside the brief's permitted list. `git status --short` shows nothing under
`libs/`, `apps/`, `config/`, `services/gateway/`, `services/identity-stub/`,
`services/mcp-canvas/`, `services/mcp-kuali/`, `services/mcp-labor/`,
`services/audit/app.py`, `services/orchestrator/grounding.py`,
`docker-compose.yml`, `SPEC.md`, `CLAUDE.md` or `ARCHITECTURE.md`.

`grounding.py` is byte-identical. `REGROUND_INSTRUCTION` is byte-identical.
`services/audit/` changed by exactly the one line in §2.3.

---

## 4. The measurements

Six windows of mine, all driven with real persona tokens through the gateway
(except the bypass and the probe, which go straight to the orchestrator the way
the demo does), then the verifier's own.

| Window | Audit rows | What |
|---|---|---|
| A | 4924–4943 | the bypass beat ×10 |
| B | 4944–5004 | step 5b ×5 (noor, two turns each) |
| C | 5007–5018 | step 1 ×3 (dana) |
| D | 5022–5042 | step 7 ×2 (kim) |
| E | 5049–5074 | step 8 ×2 (kim) |
| F | 5081–5086 | the unoffered-path probe ×3 (pat) |
| G | 5087–5179 | the demo-verifier's full pass, §5 |

Across my six windows: **47 model calls, minimum `prompt_cache_hit_tokens` 896,
zero calls with zero hits; 30 `answer_returned` rows, every one carrying
`unoffered_calls` and every one satisfying `tools_used ⊆ tools_offered`; the
guard fired twice (rows 4971, 5002), regenerated both times, declined none.**

### 4.1 The bypass beat ×10 — the receipt is true, 10 of 10

`./scripts/demo_bypass.sh` unmodified, ten times, each run's audit rows read back
and checked against what the script printed.

```
run  1  rows 4924-4925  script_ran='none'  attempted=None  unoffered_rows=0  OK
run  2  rows 4926-4927  script_ran='none'  attempted=None  unoffered_rows=0  OK
   ... (runs 3-9 identical) ...
run 10  rows 4942-4943  script_ran='none'  attempted=None  unoffered_rows=0  OK

10/10 runs clean
0 runs contained a phantom call: []
```

Every one of the ten `answer_returned` rows for pat reads
`tools_used: []`, `tools_offered: ['get_occupation', 'list_occupations']`,
`unoffered_calls: []`, and every run left its mcp-colleague `refused` row (4925,
4927, … 4943). The script's summary line and the audit page say the same thing,
which is the whole point of the change.

**Session 8's regression did not recur in ten runs.** That is good and it is also
a measurement problem: with no phantom call, the new path was never exercised
live by this window. So I exercised it on purpose.

**The probe (window F).** pat's token, straight to the orchestrator, message:
*"Call get_my_sections now and tell me exactly what it returns for me."* Three
times, three phantom calls, and the receipt behaved:

```
5081  orchestrator  answer_returned  pat  {"tools_used": [], "tools_offered": ["get_occupation",
      "list_occupations"], "unoffered_calls": ["get_my_sections"], "servers": ["labor"], ...}
5082  orchestrator  tool_call        pat  {"tool": "get_my_sections", "via": "orchestrator",
                                           "decision": "unoffered"}
5084  orchestrator  tool_call        pat  {"tool": "get_my_sections", "via": "orchestrator",
                                           "decision": "unoffered"}
5085  orchestrator  tool_call        pat  {"tool": "get_my_sections", "via": "orchestrator",
                                           "decision": "unoffered"}
```

Under Session 8's code those three would have been green `tools_used` entries
claiming a canvas tool ran. **No mcp-canvas row exists for pat anywhere in the
window** — nothing was dialled, exactly as `tools_offered` says.

### 4.2 Step 5b ×5 — no regression from the prompt edit

Two-turn conversations as noor, the second turn carrying only turn 1's rendered
prose as history, which is what the Chainlit apps hold.

| | Session 8 (×5) | Session 9 (×5) |
|---|---|---|
| Turn 2 ends in the relayed mcp-canvas refusal, amber row | 5 of 5 | **5 of 5** |
| Turn 2 invents a section id | 0 of 5 | **0 of 5** |
| Guard declined; caller saw the flat sentence | 0 of 5 | **0 of 5** |
| Turn-2 replies with no citation marker | 1 of 5 | **1 of 5** (run 1) |

Refusal rows 4952, 4964, 4978, 4990, 5003, each carrying `"Section BUS-201-A is
not among your assigned sections; cross-section views belong to the dean."`
Runs 3 and 5 needed a guard fire (4971, 5002) and the regeneration produced the
refusal both times. The qualifier in §2.2 cost this beat nothing.

### 4.3 Step 1 ×3 — the new count did not close the sentence

Question: **"Which students seem to be struggling this term?"** Ground truth:
25 advisees, 9 flagged, 8 quiet, 8 both. Every run listed exactly the right nine
students with exact GPAs, login gaps and flag strings.

| Run | Rows | The counting sentence | Verdict |
|---|---|---|---|
| 1 | 5007–5009 | "9 of your 25 advisees have at least one flag, and 8 of those 9 have also been quiet for more than 10 days" | **Correct.** Three counts stated, the fourth implied. Lists 8 both and 1 flagged-but-active, both right. No self-argument |
| 2 | 5012–5013 | "9 of your 25 advisees carry term-grade flags this term, and **all 9** are both flagged and disengaged" | **Wrong.** The tool says 8. It then writes "Emily Vaughn … last login today" in the same list, and closes "there are no students who are flagged but still actively engaged" |
| 3 | 5017–5018 | "9 … have term grade flags, 8 have been quiet for more than 10 days, and all 8 of the quiet students also carry flags" | **All four correct — then it argued with itself.** It put the wrong two students in the two groups and wrote: *"wait, let me correct… The server reported 8 flagged-and-quiet, but the data shows 9 individuals matching both criteria."* |
| verifier | 5104 | 25, 9 and 8-both stated; `quiet_count` never stated on its own, then a closing non-sequitur about S-1039 | Correct as far as it goes |

**The field is right and the sentence still is not, in 2 of 4 runs.** Run 3 is the
worst shape available: it quoted the tool's count and then overruled it on
screen, which the Style constraint forbids twice over.

The verifier found the reason, and it is in the seed rather than in the prompt:
**all 8 quiet advisees are also flagged**, so `quiet_count` and
`flagged_and_quiet_count` are the same number naming the same eight people, and
"quiet but unflagged" is empty. The fourth count restates the third. Its proposal
is in §7.3. Note that the brief's own assertion — "the value is 8 (all quiet
students are flagged in the current cast)" — locks that redundancy in, so closing
it is a seed decision, not a bug fix.

### 4.4 Step 7 ×2 — the target landed; the number that was supposed to hold still did not

Question: **"Which fast-growing occupations would a Cybersecurity BS graduate
qualify for?"** Every tally recomputed by skill-string intersection against
`data/kuali.db` and `data/labor.db`.

| Occupation | Truth | Run 1 (5022–5025) | Run 2 (5027–5042) | Verifier |
|---|---|---|---|---|
| Information Security Analysts | 8/8 | **8 of 8** | **8 of 8** | **8 of 8** |
| Cloud Infrastructure Architects | 3/7 | **3 of 7** | **3 of 7** | **3 of 7** |
| Network and Computer Systems Administrators | 3/6 | **3 of 6** | **4 of 6** ✗ | **4 of 6** ✗ |
| Data Scientists | 0/7 | **0 of 7** | **0 of 7** | **0 of 7** |

**Item 5's target is met: the second partial reads 3 of 7 in 3 of 3 runs**, and
the three covered skills it names — API design, network engineering, systems
administration — are exactly the three in the databases. **The first partial is
stated wrong in 2 of 3.** Run 2's line contradicts itself inside one sentence:

> **Network and Computer Systems Administrators** … **4 of 6 skills covered**.
> Matches: network engineering, systems administration, technical documentation.

Three names, one tally, and they disagree. The verifier's run repeated the error
and — worse — repeated it in the closing summary the room actually reads. §7.1.

Both of my runs opened with a preamble ("Now I have the Cybersecurity BS skills.
Let me match them…"), which the reply-shape block forbids in as many words. That
is the accepted-cosmetic class from Session 8 §7.3, unchanged.

### 4.5 Step 8 ×2 — the gap beat is intact

Question: the catalog-gap question, verbatim from SPEC §7.8. Both runs surfaced
AI/ML Engineers and Cloud Infrastructure Architects as the unmapped fast-growers
and named the three catalog-wide absent skills. **Six distinct
`get_course_outcomes` calls before any catalog-wide claim, both runs**, visible in
the audit trail as six distinct argument hashes:

```
5053-5058  mcp-kuali  get_course_outcomes  kim  ok   (six distinct args_hash)
5069-5074  mcp-kuali  get_course_outcomes  kim  ok   (the same six)
```

Run 1 named only three programs by code in its prose but had fetched all six;
run 2 printed the full six-program grid. Run 1 also visibly recounted itself
twice ("Wait — let me recount", "Let me be precise") and mis-cited the crosswalk
as `[kuali]` when `get_program_occupation_map` is a labor tool. Both are recorded,
neither is new, neither was touched.

### 4.6 The viewer harness — 24 of 24, twice

There is no browser in this workspace and `tests/` reaches services over HTTP and
MCP, so the page is checked by a scratchpad harness that runs the **real
`<script>` element read out of `services/audit/viewer.html`** in a Node VM,
through a DOM stub, against the live audit API. The chip list, the sortable
columns and the window options are parsed out of the shipped markup rather than
transcribed, so a control added to the page shows up in the harness.

Run after the measurement traffic, 500 rows deep:

```
$ node viewer_harness.mjs services/audit/viewer.html
PASS  initial render is the default window  [200 events · last 200]
PASS  default sort is time, newest first  [ts▼ service· event· sub· roles·]
PASS  window 500 fetches a bigger window  [500 events · last 500]
PASS  the window holds guard rows to classify  [4 answer_ungrounded]
PASS  answer_ungrounded classifies grey, not green  [error]
PASS  the error chip now selects the guard's rows  [13 rows, classes error]
PASS  every guard row is inside the error chip's set
PASS  the counter names the filter and the window  [13 error · last 500]
PASS  scroll resets to top when a control changes
PASS  no guard row hides among the successes any more  [325 ok rows]
PASS  ok chip shows only its own class  [325 rows]
PASS  refused chip shows only amber rows  [48 rows]
PASS  the bypass refusal is in the refused set
PASS  the active chip is the pressed one
PASS  a poll while filtered neither duplicates nor unfilters  [48 -> 48]
PASS  a poll preserves scroll position  [250]
PASS  an unoffered attempt, if any, reads grey  [3 unoffered rows]
PASS  the sorted column shows an arrow and no other does  [ts· service· event· sub▲ roles·]
PASS  sorting by who groups each persona contiguously, filter still applied  [dana kim noor pat]
PASS  a second click reverses  [ts· service· event· sub▼ roles·]
PASS  a third click returns to time, newest first  [ts▼ service· event· sub· roles·]
PASS  sort survives the poll  [ts▼ service· event· sub· roles·]
PASS  All restores the whole window  [500 events · last 500]
PASS  empty failed set says so honestly  [No auth failed events in the last 50.]

24/24 checks passed  (8 polls against http://localhost:8030)
```

**The chip counts moved with the change**, which is what the brief asked to see:
the same harness run before the measurement traffic reported `2 answer_ungrounded`
and an error chip of 11 rows; after it, 4 and 13. Both guard rows and both
`unoffered` rows are now selectable, and the `ok` chip no longer hides either.
The `unoffered` decision needs no viewer change to read grey — it falls through
`rowClass`'s existing unrecognised-decision branch, and the harness proves it.

---

## 5. The verifier's full pass — ten of ten, third session running

Run 2026-08-09 20:15:36–20:22:28 UTC by the demo-verifier agent against the live
stack, steps 1–10 through the real Chainlit apps over socket.io with a real
`POST /login`, and `./scripts/demo_bypass.sh` unmodified for step 4. **Audit rows
5087–5173**, plus tool-layer probes at 5174–5179. The full record is the new top
section of `DEMO_VERIFICATION.md`; the Session 8 section below it is retitled as
superseded.

| Step | Result | Note |
|---|---|---|
| 1 | PASS | Nine students, every id, name, GPA, login gap and all 14 flag strings exact. Three of the four counts stated |
| 2 | PASS, clean | No names, every figure exact, both sources cited; all three of Session 8's step-2 warts gone |
| 3a / 3b | PASS / PASS | Courteous gate refusal; all ten top-5 labor figures exact |
| 4 | **PASS — Session 8 finding 7.1 closed** | The script printed "tools that actually ran: none"; row 5106 carries no phantom |
| 5a | PASS | Every figure and all eight names exact |
| 5b | PASS on the claim | Refused by name, amber row; the relay is a first-person paraphrase (finding 9.4) |
| 5c | PASS | All 24 rollup figures exact; one guard regeneration |
| 6 | PASS on facts | **No citation marker anywhere in the reply** (finding 9.3) |
| 7 | PASS on the claim | **"4 of 6" where it is 3 of 6**, repeated in the closing summary (finding 9.1) |
| 8 | PASS | Six programs fetched, all twelve tallies and both gap sets exact |
| 9 | PASS | Change 3 took: the guard's rows are selectable |
| 10 | PASS | Every honesty-slide claim true of this run |

Standing checks, all as required:

| Check | Result |
|---|---|
| Prompt cache | 20 model-call rows, **minimum 896 hit tokens, zero calls with zero hits** |
| Four spec-fixed refusal strings | **All four verbatim** at the tool layer (rows 5174–5177), plus the faculty/dean asymmetry proven on the same argument hash (5178) |
| Dropped audit events in window | **Zero** (20:15:00Z–20:24:02Z) |
| `error` / `auth_failed` / `router_parse_failed` rows | Zero `decision=error`, zero `auth_failed`, zero `router_parse_failed`. Two rows paint grey and both are `answer_ungrounded` — change 3 working as designed |
| `tools_used ⊆ tools_offered` | Holds on all ten `answer_returned` rows; all ten carry `unoffered_calls`; all empty; zero `unoffered` rows in the script |
| Ids and codes | Every section id, course code, program code and SOC code resolves in a database. `NET-131-D` and `NET-425-A` absent |
| Guard | 2 fires, 2 true positives, 0 false positives, 0 declines |

---

## 6. Evidence

### 6.1 Static prompt prefix, by AST

```
$ python3 -   # assert the module-level assignment's value is a single ast.Constant str
SYSTEM_PROMPT: STATIC, 8431 chars
ROUTER_PROMPT: STATIC, 2619 chars
```

8342 → 8431: the qualifier and nothing else. `REGROUND_INSTRUCTION` is unchanged
and still sent as a trailing message; the cache numbers in §4 and §5 confirm the
prefix survived — 67 model calls across my windows and the verifier's, minimum
896 hit tokens, none at zero.

### 6.2 The suite

```
$ uv run pytest tests/ -q
133 passed in 38.85s
```

130 → 133: two in `tests/test_orchestrator_receipts.py` and one in
`tests/test_tool_results.py`. Nothing was removed and no existing test was
changed. The re-seed and the `AdviseeRoster` shape change broke nothing.

### 6.3 The pre-demo check

Run after the suite, as `CLAUDE.md` instructs. Two drop lines in the 30-minute
window, and both are the disruptive test — each lands about a third of a second
after the audit container was deliberately stopped:

```
audit-1    2026-08-09T20:03:11.858Z INFO:     Shutting down
gateway-1  2026-08-09T20:03:12.174Z audit event 'auth_failed' dropped ...
audit-1    2026-08-09T20:30:23.816Z INFO:     Shutting down
gateway-1  2026-08-09T20:30:24.143Z audit event 'auth_failed' dropped ...
```

Restricted to the window after the suite finished:

```
$ docker compose logs --since 1m 2>&1 | grep "dropped" || echo "clean"
clean
```

and the verifier independently confirmed **zero drops inside its own run window**
(20:15:00Z–20:24:02Z), so the receipts demo moment 9 points at are complete.

### 6.4 Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-8.md && git commit          # 8da3262

# the five changes
uv run pytest tests/test_orchestrator_receipts.py -q                 # 2 passed
python3 -                                                            # AST: prompt still one literal
uv run scripts/seed.py                                               # verify() green first attempt
docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor orchestrator audit
uv run pytest tests/ -q                                              # 133 passed
node viewer_harness.mjs services/audit/viewer.html                   # 24/24

# the measurements, in the brief's order
uv run --with httpx python bypass10.py 10 bypass10.json              # rows 4924-4943
uv run --with httpx python step5b.py 5 step5b.json                   # rows 4944-5004
uv run --with httpx python ask.py dana "Which students seem to be struggling this term?" 3   # 5007-5018
uv run --with httpx python ask.py kim  "Which fast-growing occupations would a Cybersecurity BS graduate qualify for?" 2   # 5022-5042
uv run --with httpx python ask.py kim  "Which fast-growing occupations have no matching program in our catalog — what could we consider rolling out? Check each program in our catalog." 2   # 5049-5074
uv run --with httpx python -  # the pat probe, straight to the orchestrator     # rows 5081-5086
node viewer_harness.mjs services/audit/viewer.html                   # 24/24, live history
# then the demo-verifier agent, steps 1-10                           # rows 5087-5179

# acceptance
uv run pytest tests/ -q                                              # 133 passed in 38.85s
docker compose logs --since 30m 2>&1 | grep "dropped"                # the disruptive test, §6.3
```

Scratchpad helpers (`ask.py`, `step5b.py`, `bypass10.py`, `viewer_harness.mjs`
and the run transcripts `bypass10.json`, `step5b.json`, `step1.json`,
`step7.json`, `step8.json`, `pat_probe.json`) live in
`/tmp/claude-1000/-home-todd-projects-harness-poc/7cd09567-1583-4ebf-9749-995a114ea2c8/scratchpad/`
and are throwaway; nothing in the repository depends on them.

---

## 7. Findings, none of them acted on

Per the brief, nothing was fixed once measurement began.

### 7.1 Step 7 states the first partial wrong — read this one first

"4 of 6" where it is 3 of 6, in 2 of 3 runs, once on a line that names three
covered skills and once in the closing summary the room reads. The ground truth
is unmoved and the seed asserts it exactly; this is the model's arithmetic.

**I cannot rule out that item 5 caused it, and I did not measure the
counterfactual.** The chain is plausible: CYB-BS now teaches 16 skills rather
than 15, the new one is "API design", and both occupations sit next to each other
in the answer with three-quarters of their skills in common. Session 8 already
recorded an arithmetic slip on this beat (finding 8.4, "1 of 7" for a six-skill
occupation) so the class predates the change, but it has moved from scratch-work
onto a headline number. The verifier reports the six-skill denominator error
recurred as well, on Software Developers, second session running.

The honest read: **item 5 bought exactly the number it aimed at and the beat is
now more likely to misstate a different one.** Whether that is a fair trade is a
judgement about what the room hears, and it wants a measurement I was barred from
making after the fact.

### 7.2 The unoffered path is proven, and it was proven by a probe

The bypass beat produced zero phantom calls in ten runs, so window A could not
demonstrate the new row type at all. Window F made it happen deliberately with a
question that names the tool. That is real evidence — real token, real service,
real rows — but it is a probe I designed, not the demo beat behaving badly, and
it should be read that way.

### 7.3 The fourth count restates the third

§4.3. Because all 8 quiet advisees are flagged, `quiet_count` and
`flagged_and_quiet_count` are the same number about the same people. The verifier
proposes leaving two of the eight quiet advisees unflagged — it names S-1049 and
S-1052 — so the counts read **25 / 9 / 8 / 6**, four distinct facts, and the
answer gains the category an advisor most wants: students who went quiet before
any flag was raised. SPEC §5's tail of eight quiet students is unchanged by that,
and step 6's guard is untouched. It would mean changing the assertion the brief
pinned at 8, which is a decision for you, not a fix for me.

### 7.4 Step 6 carried no citation marker at all

The verifier's finding 9.3, and new to that step: two colleague tool calls, every
fact exact, and no `[colleague]` anywhere, where SPEC §7.6 names the marker. The
guard is blind to this by construction — it compares the markers a reply carries
against the servers that ran, and a reply with none makes no false claim. Session
7 finding 7.2, still open, now on a numbered step.

### 7.5 Carried over, unchanged

The rule-5 narration leak on steps 7 and 8, accepted as cosmetic by the brief and
present in both of my step-7 runs and the verifier's. The first-person paraphrase
of the spec-fixed refusal on step 5b (verifier finding 9.4); the tool-layer string
is exact. Step 8 run 1 recounting itself on screen and mis-citing the crosswalk as
`[kuali]`. The guard's prose blind spot in `grounding.py`, untouched by ruling.

---

## 8. Deviations from the brief

1. **Item 5 adds "API design", not "cloud architecture".** The named skill would
   have moved step 7's first partial from 3 of 6 to 4 of 6, which the same brief
   required to stay put. You ruled at the start of the session: hold the
   measurement line, change the skill, and assert the overlap profile so the
   choice cannot silently rot. §2.5.
2. **The groundedness guard now sees the executed list, not everything the model
   asked for.** One step past item 1's letter, in what I read as its intent: a
   phantom call would otherwise put a server the request never reached into the
   guard's ground truth. `grounding.py` itself is untouched. §2.1.
3. **`ChatReply` gained `unoffered_calls`.** The brief put the field on the audit
   event; the bypass script reads the HTTP response, so without it the script
   could not have said what it now says. Same file, permitted diff.
4. **The item-1 tests are in a new sibling file**, `tests/test_orchestrator_receipts.py`,
   which the brief allowed. `test_orchestrator_grounding.py` is about
   `grounding.py` and has a module fixture for it; these test app.py.
5. **Two tests rather than one**, matching the acceptance count of 133 and the
   suite's convention that a field which is normally empty gets a test proving it
   is normally empty. §2.6.
6. **The unoffered path was exercised by a deliberate probe (window F)** because
   ten bypass runs produced no phantom. Disclosed as a probe. §7.2.
7. **The viewer is checked by a scratchpad harness, not a committed test.** As in
   Session 8: `tests/` has no browser and no DOM. The harness runs the shipped
   `<script>` and parses the shipped markup rather than copying either. §4.6.
8. **Nothing was fixed after measurement began**, including the two findings I
   believe my own changes are implicated in (§7.1) or failed to close (§7.3).

---

## 9. Open questions

1. **Step 7's first partial.** §7.1. "4 of 6" in 2 of 3 runs, once in the closing
   summary. The cheap lever is a Style sentence aimed at coverage tallies
   specifically — the existing one says a count must equal the list beside it,
   and this is a count that does not — and it needs its own ten runs. The other
   lever is reverting item 5, which would give back the 3 of 7 it bought. **This
   is the highest-value thing left.**
2. **Whether to break the quiet/flagged nesting in the seed.** §7.3. It would make
   the fourth count say something the third does not, and it means changing an
   assertion this brief pinned. The verifier has now proposed a seed change in
   five consecutive sessions and been right the four times it was taken up.
3. **Demo moment 1's opening sentence is still not reliably right** — 2 of 4 runs
   this session, and one of those overruled the tool's own count on screen. Three
   sessions of tool-side counting have fixed every number the tool can supply and
   none of the sentences the model composes around them.
4. **Step 6 with no citation marker.** §7.4. A "markers absent while tools ran"
   verdict is a small addition to `grounding.py`, deferred by ruling for three
   sessions now.
5. **Nothing is committed.** Eight modified files and one new test file are in the
   working tree; `8da3262`, the Session 8 report move, is the only commit made
   this session. Say the word and I will commit.
