# SESSION_REPORT — harness-poc Session 10

A decision experiment, one seed change, and one document. Not a fix session: no
prompt file was touched, nothing in `services/` was changed, and nothing found
during measurement was acted on.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

**This is a stop-point. The mode decision is yours.** Items 1 and 3 are
complete. Item 2's measurement is complete for both arms and the comparison
table is in §4. The demo-verifier's freeze-certification pass has **not** been
run, because it must run in the mode you choose.

**Headline: extended-reasoning mode removes the arithmetic defect class outright
and costs about 54% in latency.** Across the two beats the defect lives on, the
current default (`AGENT_THINKING=false`) stated a wrong number in **5 of 10
runs** and argued with itself on screen in 2 of them; with reasoning enabled it
stated a wrong number in **0 of 10** and never argued with itself. Median
latency across all beats went from **13.8s to 21.3s**. The cost is not only
time: the citation guard fired more often in the reasoning arm and declined
once, which cost demo moment 5a its answer in 1 of 3 runs — the one regression
either arm produced.

The seed change landed cleanly. `get_my_advisees` now returns **25 advisees, 9
flagged, 8 quiet, 6 both** — four distinct facts — with two advisees quiet
before any flag was raised. Every other invariant held on the first re-seed, and
`uv run pytest tests/ -q` reports **133 passed**.

---

## 1. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | Item 1: seed nesting broken, headline held at 25/9/8/6, `verify()` updated, every other invariant intact | **PASS** — green on the first re-seed, nothing retuned. §2, §7.1 |
| 2 | `pytest` green, 133 | **PASS** — 133 passed in 35.25s. §7.2 |
| 3 | Item 2: both arms measured, warmed, in the stated order, nothing fixed once measurement began | **PASS** — 4 warmups + 18 timed runs per arm. §4 |
| 4 | Zero zero-hit cache calls in either arm | **PASS** — 44 model calls per arm, minimum 896 hit tokens, zero at zero. §4.6 |
| 5 | Item 2: one comparison table, defect rates and median latency per beat per arm | **PASS** — §4.1 |
| 6 | The halt honored before any verifier pass | **PASS** — no verifier run. This report is the stop-point |
| 7 | Item 3: `docs/LESSONS.md`, all ten named findings covered | **PASS** — eleven entries plus a "what this did not prove" section. §5 |
| 8 | Diff confined to the named files | **PASS** — four files plus this one. §3 |

---

## 2. Item 1 — the seed change

Session start: `SESSION_REPORT.md` was moved to `reports/session-9.md` and that
move was committed by itself as **`5e71846`**, per `CLAUDE.md`. It is the only
commit made this session.

### 2.1 What was wrong

`flagged_courses()` flags any advisee over the quiet threshold, so every one of
dana's 8 quiet advisees was also flagged. `quiet_count` and
`flagged_and_quiet_count` were therefore both 8, naming the same eight people,
and "quiet but unflagged" was empty. Demo moment 1's opening sentence had three
facts to state and a fourth that restated the third — which is very likely why
the model kept stating three and padding (Session 9 §4.3, verifier §7.3).

### 2.2 What was built

`scripts/seed.py`, two new module-level lists and three lines inside
`flagged_courses()`:

```python
DANA_QUIET_UNFLAGGED = ["S-1049", "S-1052"]
DANA_FLAGGED_WHILE_ACTIVE = ["S-1048", "S-1051"]
```

```python
if student["id"] in DANA_QUIET_UNFLAGGED:
    return []
if student["id"] in DANA_FLAGGED_WHILE_ACTIVE:
    return current[:1]
```

The two exemptions come first, and the ordinary rule is untouched below them, so
there is still exactly one definition of "flagged" and `verify()` counts with
the same function that wrote the flags.

**The verifier's two candidates were taken as proposed** — S-1049 (Krista
Leblanc, GPA 1.94, 21 days quiet) and S-1052 (Elliot Maldonado, GPA 2.28, 23
days). Their GPAs already justify an advisor's attention and the absence of a
term flag is the point: nobody has noticed yet.

**The two who gain flags were chosen, and the choice is load-bearing in a way
worth recording.** S-1048 (Robert Valdez, GPA 2.79, logged in 3 days ago) and
S-1051 (Wesley Pham, GPA 3.02, logged in 4 days ago). Both ids are **after
S-1042**, deliberately. Writing a flag draws from the random stream, so a
student who gains or loses one resequences every student seeded after them, and
S-1042's near-complete record — asserted since Session 2 so nobody can retune
him into a slide — must not move. Choosing ids above his leaves him untouched,
and the seed output confirms he still has nothing new to take.

They take **one** flag rather than two: a student who is still showing up has
one course going wrong, not two. With S-1045 they make three flagged-and-active
advisees, so "flagged" and "quiet" are now visibly different questions in both
directions.

### 2.3 `verify()`

The flagged-and-quiet assertion moved 8 → 6, and four more were added:

- **exactly two quiet advisees carry no flag**, counted from the seeded result
  rather than from the intent list, and then checked to be exactly the two named;
- **exactly three flagged advisees are still logging in**, so the sets cannot
  start nesting again from the other direction;
- every id in both lists is one of dana's advisees, the flagged-while-active
  pair are genuinely active, and each of them actually carries a flag (a student
  with no current registration has nothing to hang one on);
- the quiet-unflagged pair are genuinely in the quiet tail.

No assertion was loosened. `uv run scripts/seed.py`, first attempt, nothing
retuned:

```
verified:
  dana advises 25, of whom 9 carry a term grade flag and 8 have not logged in for >10 days
    both flagged and quiet: 6
    quiet with no flag raised: 2 (S-1049, S-1052)
    flagged while still logging in: 3 (S-1045, S-1048, S-1051)
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
  CYB-BS vs Cloud Infrastructure Architects: 3/7 (partial)
  CYB-BS vs Data Scientists: 0/7 (miss)
  unmapped fast-growers: AI/ML Engineers, Cloud Infrastructure Architects
  skills no program teaches: containerization, deep learning, infrastructure automation
```

Every invariant the brief named is in that output and green: dana's 25/9/8, the
new 6, S-1055's three-open-one-blocked shape, S-1042, S-1049's blocked courses,
noor's two non-BUS sections, all four step-7 tallies, the absent trio, and both
unmapped fast-growers.

The four MCP servers were restarted per `CLAUDE.md`, and the result was read
back over MCP with a real dana token, not from the database:

```
{'advisee_count': 25, 'flagged_count': 9, 'quiet_count': 8, 'flagged_and_quiet_count': 6}
quiet unflagged: [('S-1049','Krista Leblanc',1.94,21), ('S-1052','Elliot Maldonado',2.28,23)]
flagged active:  [('S-1045','Emily Vaughn',2.44,0,  ['DAT-610: D at midterm','DAT-620: no submissions in 2 weeks']),
                  ('S-1048','Robert Valdez',2.79,3, ['IS-620: missing 3 assignments']),
                  ('S-1051','Wesley Pham',3.02,4,   ['HIM-310: D at midterm'])]
```

### 2.4 The test and the casting table

`tests/test_tool_results.py`: the pinned value in
`test_the_advisee_roster_counts_the_students_who_are_both` moved from 8 to 6,
and the comment no longer claims every quiet advisee is flagged. The assertions
themselves are unchanged — they check the field against the shipped rows and
against zero, which is what the brief asked for and all it asked for. The test
count is unchanged at 133.

`DEMO_VERIFICATION.md`'s casting table now records the recast row for demo
moment 1, with the four ids and the reason, so the next person to touch the seed
can see what they would be breaking.

---

## 3. The diff

```
 DEMO_VERIFICATION.md       |   2 +-
 scripts/seed.py            | 102 +++++++++++++++++++++++++++++++++++++-----
 tests/test_tool_results.py |   5 ++-
 3 files changed, 97 insertions(+), 12 deletions(-)

 docs/LESSONS.md            | new file, 466 lines
```

Plus this file, and the regenerated `data/*.db` (gitignored). Every path is
inside the brief's permitted list. `git status --short` shows nothing under
`services/`, `libs/`, `apps/`, `config/`, `scripts/demo_bypass.sh`,
`docker-compose.yml`, `SPEC.md`, `CLAUDE.md` or `ARCHITECTURE.md`. No prompts
file, `grounding.py`, or `REGROUND_INSTRUCTION` was touched.

`.env` was edited twice to flip `AGENT_THINKING` and **has been restored to
`false`**, the committed default. It is gitignored and appears in no diff.

---

## 4. Item 2 — the A/B on AGENT_THINKING

### 4.1 The comparison table

Both arms: identical questions, fresh conversations, the same order, four
personas warmed before any timed run. Defect rates are runs-with-the-defect over
runs.

| Beat | Measure | `false` (default) | `true` |
|---|---|---|---|
| **Step 1** ×5 | Stated a **wrong** count | **1 of 5** | **0 of 5** |
| | Argued with itself on screen | **2 of 5** | **0 of 5** |
| | Overruled the tool's own count | **1 of 5** | **0 of 5** |
| | Put a student in the wrong group | **3 of 5** | **0 of 5** |
| | Stated all four counts | 2 of 5 | 1 of 5 |
| | Omitted a count (correct as far as it went) | 3 of 5 | 4 of 5 |
| | Median latency | **12.7s** | 20.2s |
| **Step 7** ×5 | Stated a **wrong** tally | **2 of 5** | **0 of 5** |
| | Wrong denominator | 0 of 5 | 0 of 5 |
| | Wrong tally reached the closing summary | 1 of 5 | 0 of 5 |
| | Preamble before the answer | **5 of 5** | **0 of 5** |
| | Median preamble length | 48 words | 0 words |
| | Median latency | **19.1s** | 23.6s |
| **Step 5a** ×3 | Answered the section question | **3 of 3** | 2 of 3 |
| | Guard declined; user saw the flat sentence | **0 of 3** | **1 of 3** |
| **Step 5b** ×3 | Relayed refusal with the amber row | **3 of 3** | **2 of 3** |
| | Relayed the spec sentence verbatim | 1 of 3 | **2 of 3** |
| | Invented a section id | 0 of 3 | 0 of 3 |
| | Turn-2 reply with no citation marker | 1 of 3 | 0 of 3 |
| | Median latency | **5.0s** | 13.8s |
| **Step 2** ×2 | Named an individual student | 0 of 2 | 0 of 2 |
| | A figure that is not in the databases | 0 of 2 | 0 of 2 |
| | Median latency | **14.2s** | 22.8s |
| **All beats** | Median latency | **13.8s** | 21.3s |
| | Median reply length | 289 words | 185 words |
| | Guard fires / declines | 3 / 0 | 4 / **1** |
| | Model calls, min cache hit, zero-hit calls | 44, 896, **0** | 44, 896, **0** |

**Read it as two findings.** On accuracy, reasoning mode is not a marginal
improvement: the arithmetic defect class that has survived five sessions of
prompt and tool work is absent from all ten of its runs, and the visible
self-argument and preamble that the reply-shape block has never managed to
suppress are absent too. On cost, it is about 7.5 seconds per answer and one new
failure mode on demo moment 5.

### 4.2 How the arms were run

`AGENT_THINKING` is read once at import by `libs/harness_models/factory.py` and
flips **both** models — the gateway's router and the orchestrator's agent. The
brief said to toggle it with an orchestrator restart, so that is what was done:
`docker compose up -d --no-deps orchestrator` recreates only that container, and
the gateway kept the value it was created with. Verified before each arm:

```
$ docker inspect harness-poc-orchestrator-1 ... | grep THINKING
AGENT_THINKING=true
$ docker inspect harness-poc-gateway-1 ... | grep THINKING
AGENT_THINKING=false
```

**This isolates the agent.** The router ran non-thinking in both arms, so the
router's latency and its routing decisions are a constant, and every difference
in the table belongs to the orchestrator's model. If you choose `true`, note
that a plain `docker compose up -d` would put the router into thinking mode as
well — which is not what was measured here.

Audit windows: arm `false` rows **5486–5681** (warmups 5486–5511, timed
5512–5681); arm `true` rows **5682–5841** (warmups 5682–5707, timed 5708–5841).
Nothing was changed between the two arms except the environment variable.

### 4.3 Step 1 — the counting beat, run by run

Ground truth: 25 advisees, 9 flagged, 8 quiet, 6 both, 2 quiet-and-unflagged,
3 flagged-and-active.

| Arm | Run | Rows | What it said | Verdict |
|---|---|---|---|---|
| false | 1 | 5512–5518 | "You have 25 advisees, and 15 of them show at least one warning sign." Groups: 6 / 3 / 2, **all three exactly right** | Counts incomplete — 9 and 8 never stated. No self-argument |
| false | 2 | 5519–5523 | "Of your 25 advisees, 9 have at least one warning sign — a flag, a long absence, or both" (that set is 11). Put S-1045 in the flagged-and-quiet six; headed the active group "2 students" | **Wrong**, and it corrected itself on screen: *"Let me correct: the data says 6 flagged-and-quiet. Re-reading:…"* |
| false | 3 | 5524–5528 | Opened with all four correct: "9 of your 25 … 8 haven't logged in … Six students are both" | Then listed the wrong six and **closed by overruling the tool**: *"the true flagged-and-quiet count is 7, not 6"* |
| false | 4 | 5529–5533 | "Of your 25 advisees, 9 have at least one active concern, and 6 of those are both flagged and disengaged" | Quiet count never stated; S-1045 ("Last login today") placed inside "Both flagged and not logging in", S-1054 (25 days) inside "still logging in" |
| false | 5 | 5534–5538 | "9 of your 25 advisees carry term grade flags, and 8 are quiet… Six are both" | **Clean.** All four counts, all three groups exact |
| true | 1 | 5708–5714 | "9 of your 25 advisees carry term-grade flags, and 6 of those have also gone quiet" | Groups exact. Quiet count not stated on its own |
| true | 2 | 5715–5719 | Same shape | Groups exact |
| true | 3 | 5720–5724 | "Nine of your 25 … 6 of those 9 also haven't logged in for more than ten days" | Groups exact |
| true | 4 | 5725–5729 | "9 of your 25 … 6 of those are also disengaged" | Groups exact |
| true | 5 | 5730–5734 | "Nine of your 25 … and eight haven't logged in… Six students are both flagged and absent" | **Clean.** All four counts, all three groups exact |

**The seed change did what it was for in both arms.** Every one of the ten runs
produced the "quiet but no flags" group with exactly S-1049 and S-1052 in it,
and every one described it as the category it is — "no flags on file yet but
their GPA and disengagement put them at clear risk", "slipping under radar". The
fourth count now has something to say. What the arms differ on is whether the
model gets the other three right while saying it.

**The residual defect is the same in both arms**: the quiet count (8) is the one
number the model prefers to leave implicit, stating "9 flagged, 6 of them also
quiet" and letting the reader add the two unflagged. That is not a wrong
statement, and it is not what any of the four fields can fix.

### 4.4 Step 7 — the tallies

Ground truth, by exact skill-string intersection: Information Security Analysts
8/8, Network and Computer Systems Administrators 3/6, Cloud Infrastructure
Architects 3/7, Data Scientists 0/7.

| Arm | Run | Rows | The four headline tallies | Verdict |
|---|---|---|---|---|
| false | 1 | 5539–5555 | 8/8, 3/6, 3/7, 0/7 | All four exact |
| false | 2 | 5556–5573 | 8/8, **4/6**, 3/7, 0/7 | **Wrong** — and it names three covered skills on the same line |
| false | 3 | 5574–5589 | 8/8, 3/6, 3/7, 0/7 | All four exact |
| false | 4 | 5590–5603 | 8/8, 3/6, **2/7**, 0/7 | **Wrong** — names three covered skills, states 2, and repeats "only 2 skills" in the closing summary |
| false | 5 | 5604–5620 | 8/8, 3/6, 3/7, 0/7 | All four exact |
| true | 1 | 5735–5743 | 8/8, 3/6, 3/7, 0/7 | Exact. **But cited `[cyb-bs outcomes] [labor]`** — an invented marker where `[kuali]` was due |
| true | 2 | 5744–5752 | 8/8, 3/6, 3/7, miss stated in words | Exact; the miss described rather than tallied |
| true | 3 | 5753–5761 | 8/8, 3/6, 3/7, 0/7 | Exact |
| true | 4 | 5762–5770 | 8/8, 3/6, 3/7, miss stated in words | Exact; the miss described rather than tallied |
| true | 5 | 5771–5779 | 8/8, 3/6, 3/7, 0/7 | Exact — **and all twelve occupations tallied in one table, all twelve correct** |

Session 9's finding 9.1 — "4 of 6" where it is 3 of 6 — **reproduced in the
`false` arm** (run 2). Its mirror image appeared in run 4, on the other partial.
Both have the same shape: a line that names three matching skills and states a
different number beside them. Neither occurred in ten runs of the `true` arm.

The wrong-denominator error of Session 9 finding 9.2 did **not** recur in either
arm: every denominator in every run was correct.

**Reasoning mode also changed the tool pattern.** The `false` arm called four or
five distinct tools per run, including per-occupation lookups; the `true` arm
called three (`list_programs_catalog`, `list_occupations`,
`get_course_outcomes`) in 5 of 5. That is not a shortcut — `list_occupations`
returns each occupation's skills, so one call grounds every tally — and it is
part of why the latency gap is smaller on this beat than on step 1.

### 4.5 Step 5b — the beat that must not regress, and did once

Each run is a fresh two-turn conversation as noor, the second turn carrying only
turn 1's rendered prose as history, which is what the Chainlit apps hold.

| Arm | Run | Turn-2 rows | Outcome |
|---|---|---|---|
| false | 1 | 5630–5635 | Guard fired, regenerated, tool refused at 5632, refusal relayed **verbatim** with `[canvas]` |
| false | 2 | 5643–5647 | Refused at 5644, relayed as a first-person paraphrase, `[canvas]` |
| false | 3 | 5658–5662 | Refused at 5659, paraphrase, **no citation marker** |
| true | 1 | 5787–5794 | Guard fired, regenerated, refused at 5790, **verbatim** relay with `[canvas]` |
| true | 2 | 5802–5809 | Guard fired, regenerated, refused at 5805, **verbatim** relay with `[canvas]` |
| true | 3 | 5821–5827 | **No refusal, no amber row.** See below |

**The `true` arm's run 3 is the one regression either arm produced, and it
starts on turn 1.** Noor's own-section question was answered twice by the model
and rejected twice by the guard — both attempts cited `[colleague]` when only
canvas had run — so the guard declined and the user saw:

```
5813  answer_ungrounded  attempt 1  markers ["colleague"]  outcome regenerating
5816  answer_ungrounded  attempt 2  markers ["colleague"]  outcome declined
      reply: "I can't ground an answer to that with the tools available."
```

Turn 2 then carried that flat sentence as its history, answered about CYB-310-A
with correct figures, and closed with "**BUS-201-A** is not among your sections
this term" — true, grounded in `get_my_sections`, and **not the tool refusal**.
No call to `get_section_engagement` for BUS-201-A, no `refused` row, nothing for
demo moment 9 to point at.

So on this beat the arms trade: the `true` arm relays the spec's exact sentence
more often (2 of 2 against 1 of 3), and it is the only arm that lost the beat
entirely. The wrong-marker misfire that caused it — canvas facts cited
`[colleague]` — is Session 5 finding 6, five sessions old and untouched by any
change since.

### 4.6 Standing checks

| Check | `false` | `true` |
|---|---|---|
| Model calls in the arm window (incl. warmups) | 44 | 44 |
| Minimum `prompt_cache_hit_tokens` | **896** | **896** |
| Calls with zero cache hits | **0** | **0** |
| Orchestrator model calls | 22 | 22 |
| `tools_used ⊆ tools_offered` on every `answer_returned` | holds | holds |
| `unoffered_calls` rows | 0 | 0 |
| Grey `error` rows other than the guard's own | 0 | 0 |
| Invented section ids or program codes | 0 | 0 |
| Individual students named on step 2 | 0 | 0 |

The cache result is the one that had to hold in both arms and does: thinking
mode changes the request body, not the prompt prefix, and the prefix stayed
cached throughout.

---

## 5. Item 3 — `docs/LESSONS.md`

New file, 466 lines, plain prose, written for someone who has not read the code.
Eleven entries, each with what happened, the session reference, and what the MVP
should do about it. Every finding the brief named is covered:

| # | Entry | Sourced from |
|---|---|---|
| 1 | The context-variable identity bug in stateful MCP sessions, and the two-token probe that proved it | Session 2 §3.1 |
| 2 | `tool_error_behavior` framing an authorization refusal as "try again" | Session 2 §3.2 |
| 3 | The router closed-list lesson — describing what a role receives decides what it may ask | Session 4 §4.1 |
| 4 | Mechanical fixes held, prompt fixes regressed, with the measured record as a table | Sessions 5–10 |
| 5 | The groundedness guard: design, ledger, and both blind spots (prose server names, markerless replies) | Sessions 6–10 |
| 6 | Fabrication under refusal, and the run-10 rescue | Sessions 5 §4.2, 6 §4.1 |
| 7 | Client-held history as the structural cause of invented rosters | Session 7 §7.1 |
| 8 | `tools_used` means executed, and the unoffered receipt | Sessions 8 §7.1, 9 §2.1 |
| 9 | The model-arithmetic defect class, and what thinking mode did to it | Sessions 5–9, and §4 above |
| 10 | Seed discipline: invariants over aesthetics | Sessions 3, 8, 9, 10 |
| 11 | Prompt-cache discipline as a rule you can verify from the audit trail | SPEC §1, every session |

It closes with "What the POC did not prove" — writes, real identity, scale,
small-cell suppression, and accuracy at catalogue volume — because those are the
questions tomorrow's discussion has to answer and this build did not.

Entry 9 contains the A/B table in the form the MVP team needs it: the finding is
not "turn thinking on" but "do not ask a model to do arithmetic a tool can do,
and if you must, budget for reasoning mode on that path and measure it".

---

## 6. Deviations from the brief

1. **Only the orchestrator was recreated between arms**, per the brief's own
   wording, so the gateway's router stayed non-thinking in both. This isolates
   the agent, which I take to be the intent — but it means the table does not
   describe what a plain `docker compose up -d` with `AGENT_THINKING=true` would
   produce. §4.2.
2. **The two advisees who gain flags were chosen with ids above S-1042.** The
   brief left the choice open ("or equivalents"); flag writing draws from the
   random stream, and any id below his would have resequenced his record, which
   `verify()` protects. §2.2.
3. **They carry one flag each, not two.** A student still logging in has one
   course going wrong. This is a casting judgement; the counts are unaffected.
4. **`tests/test_tool_results.py` changed by comment only.** The brief said to
   update the pinned value to match; the pinned value in that file is the
   comment naming it, and the assertions are shape assertions that hold at 6 as
   they did at 8. Test count unchanged at 133, as the acceptance criterion
   requires.
5. **`DEMO_VERIFICATION.md` gained only the casting-table row.** Its Session 10
   verification section belongs to the verifier pass that has not run yet.
6. **`.env` was restored to `AGENT_THINKING=false`** after the measurement, so
   the stack sits in its committed default while you decide. Flipping it is one
   line and one `docker compose up -d --no-deps orchestrator`.
7. **Nothing was fixed after measurement began**, including the `true` arm's
   step-5a decline and the `false` arm's two wrong tallies.
8. **Nothing is committed** beyond the report move. Three modified files and one
   new file are in the working tree. Say the word and I will commit.

---

## 7. Evidence

### 7.1 The seed, first attempt

```
$ uv run scripts/seed.py
verified:
  dana advises 25, of whom 9 carry a term grade flag and 8 have not logged in for >10 days
    both flagged and quiet: 6
    quiet with no flag raised: 2 (S-1049, S-1052)
    flagged while still logging in: 3 (S-1045, S-1048, S-1051)
  ... (full output in §2.3) ...

$ docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
```

### 7.2 The suite

```
$ uv run pytest tests/ -q
133 passed in 35.25s
```

133 before and 133 after: no test was added, removed, or weakened. The re-seed
broke nothing — notably `test_auth.py`, which reads student ids out of result
text, and the three count tests in `test_tool_results.py`, one of which now
sees 6 where it saw 8.

### 7.3 The pre-demo check

Run after the suite, as `CLAUDE.md` instructs. Two drop lines in the hour, both
a third of a second after a deliberate audit shutdown — the disruptive test:

```
audit-1    2026-08-09T21:31:32.046Z INFO:     Shutting down
gateway-1  2026-08-09T21:31:32.394Z audit event 'auth_failed' dropped ...
audit-1    2026-08-09T21:39:07.258Z INFO:     Shutting down
gateway-1  2026-08-09T21:39:07.569Z audit event 'auth_failed' dropped ...

$ docker compose logs --since 20m 2>&1 | grep "dropped" || echo "clean"
clean
```

Both measurement arms ran after 21:39 and neither dropped an event, so the audit
rows quoted throughout this report are complete.

### 7.4 Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-9.md && git commit          # 5e71846

# item 1
uv run scripts/seed.py                                               # verify() green, first attempt
docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
uv run pytest tests/ -q                                              # 133 passed in 35.25s
curl ... mcp-colleague get_my_advisees                               # 25 / 9 / 8 / 6, live over MCP

# item 2, arm A (the default; no restart needed, verified in place)
docker inspect harness-poc-orchestrator-1 | grep THINKING            # false
uv run --with httpx python abrun.py false arm-false.json             # rows 5486-5681
uv run --with httpx python abscore.py arm-false.json

# item 2, arm B
sed -i 's/^AGENT_THINKING=false$/AGENT_THINKING=true/' .env
docker compose up -d --no-deps orchestrator                          # gateway untouched
uv run --with httpx python abrun.py true arm-true.json               # rows 5682-5841
uv run --with httpx python abscore.py arm-true.json

# back to the committed default, pending the decision
sed -i 's/^AGENT_THINKING=true$/AGENT_THINKING=false/' .env
docker compose up -d --no-deps orchestrator
docker compose logs --since 20m 2>&1 | grep "dropped" || echo "clean"
```

Scratchpad helpers (`abrun.py`, `abscore.py`, `truth.py`) and the two run
transcripts (`arm-false.json`, `arm-true.json`, `scored.json`) live in
`/tmp/claude-1000/-home-todd-projects-harness-poc/675f2492-ec4a-4f36-a663-43ffefba0108/scratchpad/`
and are throwaway; nothing in the repository depends on them. `truth.py` reads
every ground-truth figure out of `data/*.db` rather than hard-coding it, so a
re-seed cannot leave the scorer checking last week's numbers.

**How the two judgement calls were made.** Latency, cache counters, off-roster
names, invented section ids, refusal rows, guard fires, preamble length and
closing offers are all computed by `abscore.py`. Whether a reply's four counts
are right, and whether its step-7 tallies are right, were graded by reading all
36 replies against ground truth — the scorer prints every number-bearing
sentence and every occupation tally beside the true value to support that, and
the verdicts are quoted run by run in §4.3 and §4.4 so they can be checked.

---

## 8. Findings, none of them acted on

### 8.1 The `true` arm loses demo moment 5a in 1 of 3 runs — read this one first

§4.5. Two guard rejections on the same request, both for citing `[colleague]`
when only canvas ran, then the flat decline sentence on screen. That failure
then propagated: turn 2 had a useless history and never triggered the tool
refusal, so demo moment 5b lost its amber row too. The `false` arm declined zero
times in three runs, and has declined zero times in every session since Session
6. **If you choose `true`, this beat wants ten runs behind the choice before the
demo, not three.**

### 8.2 The `false` arm's wrong tallies are two-directional now

§4.4. Session 9 recorded "4 of 6" on the first partial; this session reproduced
that and also produced "2 of 7" on the second partial, which reached the closing
summary. Both lines name three matching skills next to a different number. Two
runs in five, on a beat with four numbers.

### 8.3 An invented citation marker, in the `true` arm

§4.4, run 1: `[cyb-bs outcomes] [labor]`. Kuali ran and was due a `[kuali]`; the
model wrote a description of the data instead of a server name. The guard did
not fire — it rejects markers that name servers which did not run, and this
names no server at all, which is the markerless blind spot in a new costume
(`docs/LESSONS.md` entry 5). 1 of 5, and it is a citation defect on a beat the
room reads closely.

### 8.4 The quiet count is the one the model prefers to leave implicit

§4.3. In 7 of 10 runs across both arms, the sentence is "9 flagged, of whom 6
are also quiet", leaving the reader to add the two unflagged. Nothing about that
is wrong, and no tool field can change it — the model chooses which of the four
it says out loud. The seed change achieved what it was for (the fourth count is
now a distinct fact and the new category is named in 10 of 10) but it did not
make the model state all four.

### 8.5 Carried over, unchanged

The `[colleague]`-for-canvas misfire (Session 5 finding 6), now the direct cause
of 8.1. Replies with no citation marker at all — 1 of 3 step-5b turns in the
`false` arm. The rule-5 narration leak on step 2, present in 1 of 2 `false`-arm
runs and replaced in the `true` arm by a closing caveat of the same kind. The
guard's prose blind spot, untouched by ruling for four sessions.

---

## 9. The decision, and what happens after it

**The question is whether demo moment 1 and demo moment 7 stating a wrong number
in half their runs is worth 7.5 seconds per answer and a re-measurement of demo
moment 5.**

What I would want you to weigh, stated once and not argued:

- **Session 2 already ruled on this flag**, and ruled `false`: the visible
  method narration on the synthesis beats was judged a demo feature — the room
  watching the joins being made is the claim the demo makes — and it cost half
  the latency (§6 of `reports/session-2.md`). That ruling is now contradicted on
  the accuracy axis by evidence that did not exist then. It is not contradicted
  on the narration axis: the `true` arm's answers are shorter and show no
  working.
- **SPEC §1 mandates non-thinking by default.** Choosing `true` is a spec
  deviation and should be recorded as one.
- The reasoning arm's failure is *safe* — a decline, not a wrong answer — but it
  is silent, and it lands on the beat that carries the RBAC story.
- Latency is per answer, and the demo has roughly a dozen. About 90 seconds
  across the whole script.

**After you choose**, the remaining work is one demo-verifier pass of steps 1–10
in the chosen mode as the freeze certification, with the standing checks —
prompt cache, the four spec-fixed refusal strings, dropped events, grey rows,
the guard's ledger, and `tools_used ⊆ tools_offered`. If you choose `true`,
that pass needs the orchestrator recreated first, and I would add ten runs of
demo moment 5 to it for the reason in §8.1.

**Halting here.**
