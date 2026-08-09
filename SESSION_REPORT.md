# SESSION_REPORT — harness-poc Session 8

Five changes, then one full pass, and no iteration in between. This report
stands alone: it quotes the commands run and their output, because the person
reading it has no access to the terminal it was written from.

**Headline: all four items ruled in from Session 7 closed, the audit viewer
gained its controls, and the verifier returned 10 of 10 for the second session
running.** `uv run pytest tests/ -q` reports **130 passed** (128 before).

Three of the four measured targets were met outright:

- **Step 5b no longer invents section ids.** Session 7's worst finding — "My
  sections this term are CYB-310-A, NET-131-D, and NET-425-A", two ids in none
  of the four databases, one line below demo moment 5's money line — did not
  recur in **five of five** runs, nor in the verifier's own. Better than that,
  **5 of 5 runs ended in the relayed mcp-canvas refusal with its amber row**,
  against 8 of 10 last session.
- **Demo moment 1's opening tallies now come from the tool, verbatim, 3 of 3.**
  "9 of your 25 advisees have term grade flags and 8 haven't logged in for more
  than ten days" — `flagged_count`, `advisee_count`, `quiet_count`, in that
  sentence, all three correct.
- **The seed proposal the verifier had made three sessions running is closed.**
  Kim's answer now leads with the record rather than with Canvas: "Business
  Administration (BUS-BS) is the clearest trouble spot", 25.0% quiet and a 2.81
  GPA, both `[colleague]` figures. It did that in 3 of 3 runs and in the
  verifier's.

**One target was met and one new defect was introduced in its place, and that
defect is the thing to read before the demo.** No reply anywhere claimed a tool
was unavailable when the caller held it — the sentence Session 6 called
unshippable is gone. But on the bypass beat, pat's reply now *calls* a tool pat
does not hold, and the audit row says so: row 4652 records
`tools_used: ["get_my_sections"]` beside `tools_offered: ["get_occupation",
"list_occupations"]`. Nothing was reached and nothing leaked — no MCP server was
dialled for that call — but demo moment 4 is the receipts beat, and its receipt
is now wrong. I believe my own prompt edit caused it. §7.1.

---

## 1. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | Item 1: tool-availability sentence and the current-turn roster rule promoted into the reply-shape block; SYSTEM_PROMPT one static literal, AST-verified | **PASS** — two paragraphs added, AST says STATIC, 8342 chars. §2.1, §8.1 |
| 2 | Item 2: rule 5 extended to section ids | **PASS** — and it worked: **zero guessed section ids and zero grey `error` rows** across step 2 ×3 and the verifier's run, against seven grey rows in 1 of 3 last session. §2.2, §4.2 |
| 3 | Item 3: `flagged_count` and `quiet_count` on `get_my_advisees`, computed from the shipped rows, with tests | **PASS** — both fields, two tests, and the headline states all three counts verbatim 3 of 3. §2.3, §4.1 |
| 4 | Item 4: the verifier's spread proposal applied, every casting invariant preserved | **PASS** — GPA spread 0.36, quiet spread 22.7 points; every invariant asserted and green on the first re-seed. §2.4, §4.2 |
| 5 | Item 5: viewer filter chips, window dropdown, sortable columns, all composing with the poll | **PASS** — 23 of 23 checks against the shipped script and live data. §2.5, §4.5 |
| 6 | Measurement in the stated order, nothing fixed once it began | **PASS** — four windows then the verifier; the five findings below are recorded and untouched. §4, §7 |
| 7 | `pytest` green, 130+ | **PASS** — 130 passed in 36.13s. §8.2 |
| 8 | Verifier 10/10 sustained | **PASS** — ten of ten, second session running. §5 |
| 9 | Diff confined to the named files | **PASS** — six files, all inside the permitted list; `services/audit/app.py` needed no change. §3 |

---

## 2. What was done

Session start: `SESSION_REPORT.md` was moved to `reports/session-7.md` and that
move was committed by itself as **`84dad30`**, per `CLAUDE.md`. It is the only
commit made this session.

### 2.1 Item 1 — two paragraphs promoted into the reply-shape block

`services/orchestrator/prompts.py`. Both sit in the unnumbered reply-shape
block, so they govern **first** attempts; Session 7's version of the first one
lived only in `REGROUND_INSTRUCTION`, which is sent after a guard rejection and
therefore never reached a first attempt at all.

> Never say a tool is unavailable to you, missing, or not something you hold
> when that tool is in your set, and never let such a sentence stand in for a
> call you did not make. Before writing that you cannot reach something, look at
> the tools you have and call the one that would answer the question as asked.
>
> A list of your own sections, your advisees, or any other roster comes only
> from a tool result in this conversation's CURRENT turn. If you need that list
> again, call the tool again — get_my_sections for your sections,
> get_my_advisees for your advisees. What you wrote in an earlier turn is your
> own prose, not a tool result, and a list reconstructed from it is invented.
> Never extend, complete, or recall a roster from the conversation above.

**I kept the sentence in `REGROUND_INSTRUCTION` as well rather than
deduplicating.** The brief allowed either. Removing it would have changed the
corrective instruction that Session 7 measured at 8 of 10, in a session that had
no budget to re-measure it; leaving it costs nothing but a repeated sentence.
`services/orchestrator/app.py` is byte-identical to Session 7.

### 2.2 Item 2 — rule 5 now covers section ids

Appended to rule 5, after the existing program-code clause:

> Section ids are never guessed either, and they are not built out of a program
> code. Resolve one with get_my_sections, which returns the sections you teach,
> or take it from the question or from another tool result in this run. No tool
> lists every section in a program: the engagement rollup answers by program, so
> a program-wide question is answered at the program level, not by inventing the
> section ids it might contain. A section id that is not in a tool result from
> this run is never passed to a tool.

The second sentence is a statement of fact about the tools, checked against
`services/mcp-canvas/app.py`: `get_program_engagement_rollup` returns
`program_code, sections, enrollment, pct_logged_in_this_week,
missing_submissions` and no ids at all. That is why kim had nothing to resolve
an id *from* and composed `BUS-BS-02` instead.

### 2.3 Item 3 — the roster counts its own subsets

`services/mcp-colleague/app.py`. `AdviseeRoster` gained two fields beside
`advisee_count`, both computed from the very list the result ships:

```python
return AdviseeRoster(
    advisee_count=len(advisees),
    flagged_count=sum(1 for a in advisees if a.term_grade_flags),
    quiet_count=sum(1 for a in advisees if a.last_login_days > QUIET_AFTER_DAYS),
    advisees=advisees,
)
```

`QUIET_AFTER_DAYS = 10` is a new module constant, and `get_program_summaries`
now binds it as a parameter instead of writing `> 10` inline — so an advisor's
`quiet_count` and a dean's `pct_quiet_over_10_days` cannot come to mean
different things. That is the only other change in the file. The tool docstring,
which the model reads, now ends: "advisee_count is how many there are;
flagged_count is how many carry at least one term grade flag; quiet_count is how
many have not logged in for more than ten days."

Live result over MCP with dana's token:

```
advisee_count 25, flagged_count 9, quiet_count 8
```

### 2.4 Item 4 — the seed's per-program spread

`scripts/seed.py`. The verifier proposed this in Sessions 5, 6 and 7 and it was
never taken up. Each program now draws GPA around its own mean and carries its
own share of quiet students:

```python
PROGRAM_PROFILE: dict[str, tuple[float, int]] = {
    "BUS-BS": (2.80, 19),
    "HIM-BS": (3.05, 11),
    "CS-BS": (3.15, 6),
    "IS-MS": (3.15, 6),
    "CYB-BS": (3.15, 6),
    "DAT-MS": (3.30, 2),
}
```

**The random stream was kept in step deliberately.** The GPA draw and the three
login draws happen for every student either way; only the mean and the weights
differ. So program assignment, name pairing and the shuffle are untouched, and
the shift lands on values rather than on sequence.

`verify()` gained three assertions and now prints the spread:

- dana's **9 flagged** advisees, counted with a new `flagged_courses()` helper
  that is the same function the writer uses — a guard counting flags by a
  different rule than the one that wrote them would be checking nothing;
- the worst-to-best **average GPA spread ≥ 0.30**;
- the worst-to-best **quiet-share spread ≥ 10 percentage points**.

Output of `uv run scripts/seed.py`, first attempt, nothing retuned:

```
verified:
  dana advises 25, of whom 9 carry a term grade flag and 8 have not logged in for >10 days
  program spread: GPA 0.36, quiet share 22.7 points
    BUS-BS  avg GPA 2.81, quiet 25.0%
    CS-BS   avg GPA 3.10, quiet 8.2%
    CYB-BS  avg GPA 3.17, quiet 9.1%
    DAT-MS  avg GPA 3.14, quiet 2.3%
    HIM-BS  avg GPA 3.06, quiet 10.4%
    IS-MS   avg GPA 3.11, quiet 8.8%
  demo moment 6 asks about S-1055 (Leon Cline, CS-BS)
    taking now: CS-210
    next term:  CS-310, CS-350, CS-410
    blocked:    CS-460
  S-1042 keeps his own answer: nothing new next term, 1 blocked
  S-1049 blocked out of: BUS-201, BUS-310, BUS-330, BUS-410, BUS-460
  noor teaches CYB-310-A, CYB-210-A and no BUS section
  fast-growing means >= 20.0% (6 of 12 occupations)
  CYB-BS vs Information Security Analysts: 8/8 skills (strong)
  CYB-BS vs Network/Systems Administrators: 3/6 (partial)
  CYB-BS vs Data Scientists: 0/7 (miss)
  unmapped fast-growers: AI/ML Engineers, Cloud Infrastructure Architects
  skills no program teaches: containerization, deep learning, infrastructure automation
```

Every casting invariant the brief named is in that output and green: dana's
25/9/8, S-1055's three-open-one-blocked shape, S-1042 with nothing new to take,
noor's two non-BUS sections, the CYB trio, and both unmapped fast-growers. No
assertion was loosened and none had to be — the first re-seed passed.

**One honest shortfall against the proposal's letter.** The verifier asked for
DAT-MS "near 3.3"; it lands at **3.14**, because that cohort happens to draw
low and the mean shift preserves the noise rather than erasing it. Pushing its
mean higher would have lifted S-1045 (2.44) above the 2.5 flag threshold and
taken dana's flagged count from 9 to 8, breaking a casting invariant to fix a
cosmetic one. The spread that matters — one program visibly in trouble — is
carried by BUS-BS at both ends, and the assertions are on the spread, not on any
one program's figure.

`data/*.db` were regenerated and the four MCP servers restarted, per
`CLAUDE.md`.

### 2.5 Item 5 — the audit viewer's controls

`services/audit/viewer.html` only. **`services/audit/app.py` was not touched**:
`GET /events` already clamps with `min(limit, 1000)`, so `limit=500` is honored
as it stands. Checked before writing any of it:

```
$ curl -s "http://localhost:8030/events?limit=500" | ...
500 rows returned for limit=500
```

- **Filter chips** — All · ok · refused · error · auth failed. The chip filter
  and the row colours read **the same `rowClass(ev)` function**, so they cannot
  disagree; `filter === "all" ? events : events.filter(ev => rowClass(ev) === filter)`
  is the whole of it. The active chip is filled, not tinted — from the back of a
  room a border colour is not a state.
- **The chips replaced the legend.** The legend named three colours and could
  not be clicked; the chips carry the same coloured dots, filter to them, and
  add the grey `error` class the legend never explained. One row of header
  instead of two.
- **Window** — a dropdown for last 50/100/200/500 driving the `limit=`
  parameter, default 200.
- **They compose honestly.** The counter reads `34 refused · last 500`: it says
  what it filtered and what it filtered *within*. An empty result says
  `No auth failed events in the last 50.` rather than looking broken.
- **Sortable columns** — Time, Service, Event, Who, Roles. Sorting reads the
  event fields (`Date.parse(ev.ts)`, strings elsewhere), never the rendered
  cell: the "—" that stands in for an absent `sub` on screen would otherwise
  sort among the letters. First click ascending, second reversed, third back to
  time-descending; ▲/▼ on the active column in a fixed-width span so switching
  it on does not shift the heading. Ties break on row id, so same-second rows do
  not shuffle on every poll.
- **Filter first, then sort**, applied on every render, which is why new events
  arriving on the poll land in their sorted position instead of at the top.
- A poll restores the scroll position; changing a control resets it to the top
  deliberately, because what the reader is looking at has changed.

No framework, no build step, no new dependency.

### 2.6 Tests

`tests/test_tool_results.py`, +67 lines, two new tests — one per new count
field, matching the file's existing one-test-per-count convention:

- `test_the_advisee_roster_counts_its_own_flagged_students` — `flagged_count`
  present, equal to the number of advisees carrying a term grade flag, and
  greater than zero.
- `test_the_advisee_roster_counts_its_own_quiet_students` — `quiet_count`
  present, equal to the number over the ten-day threshold, and greater than
  zero.

The greater-than-zero assertions exist because a count of zero would satisfy the
equality while telling the demo nothing. Both run against the live stack with a
real dana token, like everything else in `tests/`.

---

## 3. The diff

```
 DEMO_VERIFICATION.md             | 786 ++++++++++++++++++++++++++++++++++++++-
 scripts/seed.py                  | 110 +++++-
 services/audit/viewer.html       | 219 +++++++++--
 services/mcp-colleague/app.py    |  33 +-
 services/orchestrator/prompts.py |  19 +
 tests/test_tool_results.py       |  67 ++++
 6 files changed, 1184 insertions(+), 50 deletions(-)
```

Plus this file, and the regenerated `data/*.db` (gitignored). Every path is
inside the brief's permitted list, and two permitted paths were not needed:
`services/audit/app.py` (the cap was already 1000) and `tests/` beyond the one
file. `git status --short` shows nothing under `libs/`, `apps/`, `config/`,
`services/gateway/`, `services/identity-stub/`, `services/mcp-canvas/`,
`services/mcp-kuali/`, `services/mcp-labor/`, `services/orchestrator/app.py`,
`services/orchestrator/grounding.py`, `docker-compose.yml`, `SPEC.md`,
`CLAUDE.md` or `ARCHITECTURE.md`.

`grounding.py` is untouched, as instructed.

---

## 4. The measurements

Four windows of mine, all driven through the gateway with real persona tokens,
then the verifier's own.

| Window | Audit rows | What |
|---|---|---|
| A | 4516–4528 | step 1 ×3 (dana) |
| B | 4531–4553 | step 2 ×3 (kim) |
| C | 4558–4615 | step 5b ×5 (noor, two turns each) |
| D | 4619–4628 | step 6 ×2 (dana) |
| E | 4633–4718 | the demo-verifier's full pass, §5 |

Across my four windows: **35 model calls, minimum `prompt_cache_hit_tokens`
896, zero calls with zero hits; zero grey `error` rows; the guard fired once
(row 4602), was right, and its regeneration produced the refusal.**

Dana's three step-1 runs and kim's three step-2 runs use the identical question,
so the dana half of "step 2 ×3 per persona" is window A.

### 4.1 Step 1 ×3 — the headline tallies, and where the counting went next

Question: **"Which students seem to be struggling this term?"** Ground truth
from `data/colleague.db`: dana advises **25**, of whom **9** carry a term grade
flag and **8** have been quiet over ten days. All 8 quiet students are also
flagged, so the flagged set is those 8 plus S-1045.

**All three runs opened with all three counts, verbatim from the tool:**

| Run | Opening sentence |
|---|---|
| 1 | "9 of your 25 advisees have term grade flags and 8 haven't logged in for more than ten days." |
| 2 | "9 of your 25 advisees carry at least one term grade flag, and 8 haven't logged in for more than ten days." |
| 3 | "9 of your 25 advisees have term grade flags, and 8 haven't logged in for more than 10 days." |

Session 5 said "23 advisees"; Session 6's verifier said "24"; Session 7 fixed
the total and then said "Eight of your 25 advisees have active flags" above a
list of nine, 3 of 3. **That sentence is now correct, 3 of 3.** All three runs
also named exactly the right nine flagged students, checked by script against
all 300 names in the database, with **zero off-roster students named**.

**What went wrong instead, and it is one level further in.** Runs 1 and 2
sub-divide the roster into "flagged and quiet" versus "flagged but active" and
get the split wrong — run 1 says three are both when eight are, run 2 says four
— then notice mid-answer and argue with themselves in the reply:

> **Quiet but no flags (5 more beyond those above):** … all accounted for in the
> lists above. The remaining two quiet students without flags are **Emily
> Bryant** (already listed for flags) and none; of the 8 quiet, 6 have flags and
> the other 2 are S-1031 … — actually all 8 quiet students appear above.

It arrives at the truth and the truth is in there, but the visible self-argument
is the shape the reply-shape block forbids in as many words. **Run 3 is clean**
and is what the beat should look like: nine flagged listed under a "9 students"
heading, eight quiet listed under an "8 students" heading, both exact.

This is the same defect class as Session 7's, moved: the model now takes the
counts it is given and goes wrong on the intersection it derives for itself. A
tool cannot supply that number today. §7.4.

### 4.2 Step 2 ×3 — the seed change lands

Same question, as kim. **All three runs lead with BUS-BS on `[colleague]`
figures.** Run 1's first line:

> **Business Administration (BUS-BS) is the clearest trouble spot, with deep
> disengagement compounded by low academic performance.**

and it gets there on the record's own numbers — 25.0% quiet, 2.81 GPA — before
Canvas is mentioned. Session 7 recorded a flat list spanning 3.00 to 3.17 GPA
and 2.3% to 9.1% quiet, five of six inside a point, with the spread only
appearing when the answer reached the rollup. **That is closed.**

Every figure was checked cell by cell against `data/colleague.db` and
`data/canvas.db` and every one is exact — the six GPAs, the six quiet
percentages, the six login rates (63.6 / 77.4 / 80.0 / 86.0 / 89.7 / 95.0), the
six missing-submission counts, the section counts, and run 1's enrollment trend
claim ("BUS-BS grew from 45 (2025SP) to 50 (2026SP)" — the table says 45 and 50).

| Check | Session 7 | Session 8 |
|---|---|---|
| Guessed section ids | 7, in 1 of 3 runs | **0 of 3** |
| Grey `error` rows behind step 2 | 7 | **0** |
| Individual students named | 0 | **0 of 3** — no names, no `S-\d{4}` ids |
| Reply claiming a tool it holds is unavailable | 1 (the verifier's run) | **0 of 3** |
| Leads with the colleague-side spread | no | **3 of 3** |

**Run 3 leaked its deliberation, and the new rule is why.** It opens:

> Now I need to see the section-level detail. The program engagement rollup
> gives me section counts per program but not individual section IDs. Let me
> look at what I can access … I don't have a tool that lists all sections.

Every sentence there is *true* — it is close to a paraphrase of the clause I
added to rule 5 — and it did the right thing: it called no section tool and
invented no id. But it is a preamble, and preambles are forbidden two paragraphs
higher in the same prompt. The rule bought correct behaviour and paid for it in
narration, 1 of 3. §7.3.

### 4.3 Step 5b ×5 — the invented-section-id defect is closed

Each run is a fresh two-turn conversation as noor: **"How is my CYB-310 section
doing this week?"**, then **"And how's BUS-201-A doing?"**, with the second turn
carrying only turn 1's rendered prose as history — exactly what the Chainlit
apps hold, which is the condition that produced the defect.

| | Session 7 (×10) | Session 8 (×5) |
|---|---|---|
| Turn 2 invents section ids | 1 of 1 verifier run | **0 of 5** |
| Turn 2 ends in the relayed refusal, with the amber row | 8 of 10 | **5 of 5** |
| Guard declined; caller saw the flat sentence | 2 of 10 | **0 of 5** |
| Fabricated BUS-201-A roster | 0 of 10 | **0 of 5** |
| Claim that a held tool is unavailable | 0 of 10 | **0 of 5** |

**Not one turn-2 reply listed noor's sections at all.** The defect was that the
model needed a section list nobody had asked for and composed one; the new
paragraph appears to have removed the impulse rather than merely correcting the
list. Every run wrote its own `refused` audit row: 4566, 4578, 4590, 4603, 4615,
all carrying `"Section BUS-201-A is not among your assigned sections;
cross-section views belong to the dean."`

Runs 1 and 4 relayed that sentence to the screen word for word. Runs 2, 3 and 5
paraphrased it ("I don't teach BUS-201-A, so I can't see its engagement data.
Only the dean can pull cross-section views."). As Session 7 noted, the verbatim
string is guaranteed at the tool layer and in the audit row; on screen it is the
model's paraphrase.

**One wart: run 5's turn 2 carries no citation marker at all.** That is Session
7 finding 7.2, unchanged and untouched by ruling — the guard is blind to it by
construction. 1 of 5.

Run 4's guard fire is worth recording as the mechanism working: attempt 1 cited
`[canvas]` having called nothing (row 4602), the guard rejected it, and the
regeneration called `get_section_engagement`, which refused at row 4603.

### 4.4 Step 6 ×2 — no regression

**"What should S-1055 take next term?"** Both runs offered CS-310, CS-350 and
CS-410, blocked CS-460 correctly, transcribed the licence from `open_because`,
and stated no false facts. The re-seed moved the grades, and both runs moved
with it — checked against the database:

```
S-1055 Leon Cline, CS-BS, GPA 3.41, 3 days since login, 9 credits
completed: CS-101 2024FA A, CS-201 2024FA C, CS-320 2025SP A
registered: CS-210        seats: CS-310 36, CS-350 21, CS-410 35
```

Run 2, verbatim, against that record:

> - **CS-310 Algorithms** — 3 credits, 36 seats. Prerequisite CS-201 satisfied (completed 2024FA, C). [colleague]
> - **CS-350 Software Engineering** — 3 credits, 21 seats. Prerequisite CS-201 satisfied (completed 2024FA, C). [colleague]
> - **CS-410 Cloud Architecture** — 3 credits, 35 seats. Prerequisite CS-320 satisfied (completed 2025SP, A). [colleague]

Every figure exact, both runs.

### 4.5 The viewer, checked against the shipped script

The page has no test file — `tests/` reaches services over HTTP and MCP, and
there is no browser in this workspace. So the checks drive **the real `<script>`
element read out of `services/audit/viewer.html`** in a Node VM, through a DOM
stub that implements only what the page uses, against the live audit API. That
exercises the shipped code rather than a transcription of it; the harness is a
throwaway in the scratchpad and nothing in the repository depends on it.

Run against this session's own audit history, 500 rows deep:

```
$ node viewer_harness.mjs services/audit/viewer.html
PASS  initial render is the default window  [200 events · last 200]
PASS  default sort is time, newest first  [ts▼ service· event· sub· roles·]
PASS  window 500 fetches a bigger window  [200 -> 500; 500 events · last 500]
PASS  scroll resets to top when a control changes  [0]
PASS  refused chip shows only amber rows  [39 rows, classes refused]
PASS  counter names the filter and the window  [39 refused · last 500]
PASS  the bypass refusal is in the refused set
PASS  the step-5b refusal is in the refused set  [11 noor refusals]
PASS  the active chip is the pressed one  [false,false,true,false,false]
PASS  a poll while filtered neither duplicates nor unfilters  [39 -> 39]
PASS  sorting by who groups each persona contiguously, filter still applied
      [dana×7 kim×7 noor×11 pat×14]
PASS  the sorted column shows an arrow and no other does  [ts· service· event· sub▲ roles·]
PASS  a second click reverses  [ts· service· event· sub▼ roles·]
PASS  a third click returns to time, newest first  [ts▼ service· event· sub· roles·]
PASS  reversal actually reversed the grouping
PASS  sort survives the 2-second poll  [ts· service▲ event· sub· roles·]
PASS  a poll preserves scroll position  [250]
PASS  changing the filter resets scroll  [0]
PASS  All restores the whole window  [500 vs 500; 500 events · last 500]
PASS  ok chip shows only its own class  [47 rows, ok]
PASS  refused chip shows only its own class  [3 rows, refused]
PASS  empty error set says so honestly  [No error events in the last 50.]
PASS  empty failed set says so honestly  [No auth failed events in the last 50.]

23/23 checks passed
```

Every check the brief named is in that list, including the two composition
questions — "refused · last 500" isolating the amber rows with both the bypass
and a step-5b refusal among them, and a poll landing mid-filter neither
duplicating a row nor moving the scroll.

The layout was checked separately with a headless Firefox screenshot at
1600×900: one header row, chips right-aligned with the window dropdown, the
active chip filled, and `TIME▼` on the sorted column before the first response
lands.

---

## 5. The verifier's full pass — ten of ten, again

Run 2026-08-09 19:06:03–19:15:17 UTC by the demo-verifier agent against the live
stack, steps 1–10 through the real Chainlit apps over socket.io with a real
`POST /login`, and `./scripts/demo_bypass.sh` unmodified for step 4. **Audit rows
4633–4718.** The full record is the new top section of `DEMO_VERIFICATION.md`;
the Session 7 section below it is retitled as superseded.

**All ten steps PASS.** Two clean sweeps in a row, after Session 5 and Session 6
each returned nine of ten.

Its own summary of the five changes: changes 1–4 took, and change 5 improves
demo moment 9. Specifically —

- Session 7 finding **7.1 is closed**: `NET-131-D` and `NET-425-A` return zero
  across all four `sqlite3 .dump`s and appear nowhere in the run; step 5b is one
  flat sentence, the tool's refusal verbatim with a `[canvas]` marker.
- **No section id or program code in the whole run is absent from a database.**
- `get_my_advisees` returns `advisee_count 25, flagged_count 9, quiet_count 8`
  at the tool layer and step 1's headline states them verbatim.
- Kim's step 2 **leads with BUS-BS** on the record's figures, with Canvas
  corroborating rather than competing.

Standing checks, all as required:

| Check | Result |
|---|---|
| Prompt cache | 20 model-call rows, **minimum 896 hit tokens, zero calls with zero hits** |
| Four spec-fixed refusal strings | **All four verbatim** at the tool layer, plus the faculty/dean asymmetry proven |
| Dropped audit events in window | **Zero** (19:05:00Z–19:16:05Z) |
| Grey `error` rows | **Zero**, and zero `auth_failed`, zero `router_parse_failed` |
| Guard | 1 fire, 1 true positive, 0 false positives, 0 escapes (3 fires last session) |
| Answers with no citation marker | 1 — step 4 |
| False "tool unavailable" claims | **None** |

---

## 6. What the verifier said about the viewer

Worth reading before demo moment 9, because both points are about what is on
screen rather than about correctness:

> The chips are a real gain — clicking "refused" isolates the three refusals of
> the whole demo on one screen.

> `answer_ungrounded` has no `decision` field so it classifies **green** and no
> chip selects it, meaning row 4663 (the guard catching a fabrication, the most
> interesting row in the run) hides among the successes; and on a clean run
> "error" and "auth failed" are both empty, which is a good beat if it is
> deliberate and a surprise if it is not.

The first is a fair criticism of a classification I did not change: `rowClass`
has read `detail.decision` since Session 1, and `answer_ungrounded` carries no
decision. Making the guard's own rows selectable is a one-line addition to
`rowClass` — and it would change the row colours as well as the chips, which is
why I did not make it after measuring. The second is a presenter's note, not a
defect: pressing "auth failed" on a clean run and getting "No auth failed events
in the last 200" is a fine thing to do on purpose and a bad thing to discover.

---

## 7. Findings, none of them acted on

Per the brief, nothing was fixed once measurement began.

### 7.1 The bypass reply calls a tool pat does not hold — read this one first

On demo moment 4, pat's reply through the orchestrator produced this audit row:

```
4652  orchestrator  answer_returned  pat [adjunct]
      {"tools_used": ["get_my_sections"],
       "tools_offered": ["get_occupation", "list_occupations"],
       "servers": ["labor"], "regenerated": false, "ungrounded": false}

4653  orchestrator  tool_call  pat  {"tool": "get_my_sections", "via": "orchestrator"}
```

**Nothing was reached and nothing leaked.** `tools_offered` proves the registry
filtering held — pat was never given the tool — and there is no mcp-canvas row
for pat anywhere in the run, so no server was dialled. The direct bypass was
refused by mcp-colleague at row 4654 exactly as the demo claims. The security
story is intact.

**The receipt is what is wrong**, and demo moment 4 is the receipts beat. The
verifier found the mechanism: `tools_called` in
`services/orchestrator/app.py` collects every `ToolCallPart` in the run,
including a call to a tool that does not exist, and that flows into
`tools_used`, into a green audit row, and into the bypass script's own summary
line — which printed `tools the model actually called: ['get_my_sections']` two
lines above its narration that pat's non-labor tools "were never placed in the
model's view. Not refused — absent." Both cannot read as true to a watching
room.

**I think my change caused it, and I checked rather than guessed.** Across the
last 1000 audit rows — back to row 3719, the start of Session 7 — this is the
**only** `answer_returned` row where a used tool was not an offered one. The
tool the model reached for, `get_my_sections`, is one of the two named by name
in the paragraph I added, which reaches every caller including pat, and it is
paired there with an instruction to call a tool rather than say it cannot reach
something. That is a plausible enough chain that I would not ship the paragraph
unchanged without testing the alternative.

Two candidate fixes, neither measured, both one line: drop the two tool names
from the promoted paragraph so it says "call the tool again" without naming
which; or filter `tools_called` against the offered set in
`services/orchestrator/app.py` so the receipt can only name a tool that existed.
The second is the more honest fix and touches a file outside this session's
permitted diff.

### 7.2 Step 2 claimed to hold a tool it does not hold

The inverse of Session 7 finding 7.3, and probably the same cause as 7.1. Kim's
step-2 answer says "I do have `get_my_sections` which would return sections I
teach"; row 4644 lists her ten offered tools and it is not among them. Session 7
had a reply claiming it *lacked* a tool it held; that direction is now zero
across everything measured, and this direction has appeared.

### 7.3 The new rule-5 clause leaks into the prose

Step 2 run 3 (§4.2) and the verifier's step 2 both narrate their reasoning about
section ids — "Wait — I don't have a tool that lists all sections" — which is
true, is what the rule says, and is exactly the preamble shape the reply-shape
block forbids. The verifier's step 2 also closed with "If you can supply the
section IDs… I can pull the per-student detail", which rule 3 forbids in as many
words. Correct behaviour, wrong prose, on the beat that runs side by side with
step 1.

### 7.4 Derived subset counts, one level in

§4.1. The counts the tool supplies are now right every time; the intersection
the model derives — how many advisees are both flagged and quiet — is wrong in 2
of 3 runs, and one of those argues with itself on screen while getting there.
The verifier proposes a `flagged_and_quiet_count` field, which would close the
last vague phrase in the run's best answer. That is one more field in
`services/mcp-colleague/app.py` and one more seed assertion.

### 7.5 Carried over, unchanged

Answers with no citation marker at all (step 5b run 5; the verifier's step 4) —
Session 7 finding 7.2, and the guard is blind to it by design. The guard's prose
blind spot in `grounding.py`, untouched by ruling. Step 7's scratch-work tally
saying "1 of 7" for a six-skill occupation.

---

## 8. Evidence

### 8.1 Static prompt prefix, by AST

Run after both prompt edits. `CLAUDE.md`'s hard rule and SPEC §1 require a plain
constant; nothing in the committed suite checks it.

```
$ python3 -   # assert the module-level assignment's value is a single ast.Constant str
SYSTEM_PROMPT: STATIC, 8342 chars
ROUTER_PROMPT: STATIC, 2619 chars
```

7065 → 8342: the two promoted paragraphs and the rule-5 clause, and nothing
else. `ROUTER_PROMPT` lives in the gateway, which was not touched this session.
The cache numbers in §4 and §5 confirm the prefix survived — 55 model calls
across my windows and the verifier's, minimum 896 hit tokens, none at zero.

### 8.2 The suite

```
$ uv run pytest tests/ -q
130 passed in 36.13s
```

128 → 130: the two new tests in `tests/test_tool_results.py`. Nothing was
removed and no existing test was changed. Notably the re-seed broke nothing:
`test_auth.py` reads student ids out of result text, and the ids it depends on
did not move.

### 8.3 The pre-demo check

Run after the suite, as `CLAUDE.md` instructs. Four drop lines in a two-hour
window, and every one of them is the disruptive test — each lands about a third
of a second after the audit container was deliberately stopped:

```
audit-1    2026-08-09T18:02:51.482Z INFO:     Shutting down
gateway-1  2026-08-09T18:02:51.930Z audit event 'auth_failed' dropped ...
audit-1    2026-08-09T18:22:25.911Z INFO:     Shutting down
gateway-1  2026-08-09T18:22:26.243Z audit event 'auth_failed' dropped ...
audit-1    2026-08-09T18:55:14.041Z INFO:     Shutting down
gateway-1  2026-08-09T18:55:14.381Z audit event 'auth_failed' dropped ...
audit-1    2026-08-09T18:56:22.253Z INFO:     Shutting down
gateway-1  2026-08-09T18:56:22.568Z audit event 'auth_failed' dropped ...
```

The first two are Session 7's; the second two are my two suite runs. Restricted
to the window since the suite finished:

```
$ docker compose logs --since 25m 2>&1 | grep "dropped" || echo "clean"
clean
```

and the verifier independently confirmed **zero drops inside its own run
window** (19:05:00Z–19:16:05Z), so the receipts demo moment 9 points at are
complete.

### 8.4 Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-7.md && git commit          # 84dad30

# the five changes
python3 -                                                            # AST: prompt still one literal
uv run scripts/seed.py                                               # verify() green first attempt
docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
docker compose restart orchestrator
curl -s "http://localhost:8030/events?limit=500"                     # the cap is already 1000
node viewer_harness.mjs services/audit/viewer.html                   # 23/23
uv run pytest tests/ -q                                              # 130 passed in 36.13s

# the measurements, in the brief's order
uv run --with httpx python ask.py dana "Which students seem to be struggling this term?" 3   # rows 4516-4528
uv run --with httpx python ask.py kim  "Which students seem to be struggling this term?" 3   # rows 4531-4553
uv run --with httpx python step5b.py 5                                                       # rows 4558-4615
uv run --with httpx python ask.py dana "What should S-1055 take next term?" 2                # rows 4619-4628
node viewer_harness.mjs services/audit/viewer.html                                           # 23/23, live history
# then the demo-verifier agent, steps 1-10                                                   # rows 4633-4718

# acceptance
docker compose logs --since 25m 2>&1 | grep "dropped" || echo "clean"
```

Scratchpad helpers (`ask.py`, `step5b.py`, `viewer_harness.mjs`) live in
`/tmp/claude-1000/-home-todd-projects-harness-poc/3abd45da-9e16-495d-a65d-065e82c60b50/scratchpad/`
and are throwaway; nothing in the repository depends on them.

---

## 9. Deviations from the brief

1. **`REGROUND_INSTRUCTION` keeps its copy of the tool-availability sentence.**
   The brief allowed either; deduplicating would have changed an instruction
   measured at 8 of 10 in a session with no budget to re-measure it. §2.1.
2. **`services/audit/app.py` was not edited.** The brief permitted a limit-cap
   change if one was needed; `GET /events` already clamps at 1000, verified with
   a live `limit=500` returning 500 rows before any viewer work began. §2.5.
3. **The legend was replaced by the chips** rather than kept beside them. Same
   colours, same words, now clickable, plus the grey `error` class the legend
   never named — and one header row instead of two on a projector. §2.5.
4. **DAT-MS lands at 3.14 average GPA, not "near 3.3" as the proposal asked.**
   Raising it further would have unflagged S-1045 and broken dana's 9-flagged
   invariant, which the brief told me to protect. §2.4.
5. **The new tests are two, one per field**, rather than one test asserting
   both, matching the file's existing one-test-per-count convention.
6. **The viewer is checked by a scratchpad harness, not a committed test.**
   `tests/` has no browser and no DOM; the harness runs the shipped `<script>`
   rather than a copy, and it is disclosed rather than added to the suite. §4.5.
7. **Nothing was fixed after measurement began.** The five findings in §7,
   including the one I believe my own change caused, are recorded and untouched.

---

## 10. Open questions

1. **The bypass receipt names a tool that was never dialled.** §7.1. It is the
   only regression I found, it is on demo moment 4, and the likeliest cause is
   the paragraph I added. Two one-line fixes exist; the better one is in
   `services/orchestrator/app.py`, outside this session's diff. **This is the
   highest-value thing left, and it wants ten runs of the bypass beat behind
   whichever fix you pick.**
2. **Whether to name tools in the static prompt at all.** "Call get_my_sections
   for your sections" reaches every caller, including the ones who hold neither
   tool. Removing the two names costs the paragraph some concreteness and may
   cost some of its effect on step 5b, which is currently 5 of 5 — so it is a
   trade, not a free fix, and it needs its own measurement.
3. **The guard's own rows are invisible to the new chips.** `answer_ungrounded`
   carries no `decision`, so it classifies green. Making it selectable means
   changing `rowClass`, which changes the row colours too. §6.
4. **`flagged_and_quiet_count`.** The verifier's proposal, and the natural end
   of the road this session walked: the last count the model still derives for
   itself on demo moment 1 is the one it still gets wrong. §7.4.
5. **The second partial match in step 7 is thin** — Cloud Infrastructure
   Architects at 2 of 7, which the model itself calls short of half, against
   SPEC §5's "partially cover two others". The verifier suggests adding
   `cloud architecture` to a CYB-BS outcome to make it 3 of 7, and warns off
   `containerization`, whose catalog-wide absence is load-bearing for step 8.
6. **Nothing is committed.** Six modified files are in the working tree;
   `84dad30`, the Session 7 report move, is the only commit made this session.
   Say the word and I will commit.
