# SESSION_REPORT — harness-poc Session 13

The last session. Four small pieces of work and one certification: a tool fix
with a pattern that has now held six times for six, one line of registry, one
key in one audit call, one measurement with no fix permitted, and the final
demo-verifier pass.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

## The headline, in four sentences

**All three changes were built, all three were verified, and the certification
is 9 of 12.** The change that mattered most — the rollup totals — closed the
beat Session 12 failed on: step 5c stated the true cross-program total, 112,
verbatim from the tool in 5 of 5 measured runs and again in the certification
pass, where Session 12 had produced 78. The skill is now scoped by the registry
rather than by a sentence in a document, and a refused skill renders amber on
the receipts page.

**The three beats that failed are all older than this session and none of them
is in a beat this session touched.** Steps 2 and 2b state one derived ratio
wrong (the same error, in both arms, so the skill neither causes nor catches
it); step 7 states one denominator wrong, which is Session 9 finding 9.2 and
Session 11 §5.3 exactly. Per the brief's own rule, they are reported against
their session of origin and were not fixed after measurement began.

**The pre-authorized halt did not fire.** It was scoped to item 1's ×5 failing
or the certification failing 5c again. Item 1 passed 5 of 5 and 5c passed. The
work is committed.

**The attribution question is answered, and the answer is "no effect".** Ten
runs, five per arm: the skill neither improves nor degrades citation
attribution. §5 has the numbers, and the finding that outlives them is the rate
itself — two replies in five sign both servers' figures with one marker,
regardless of register.

---

## 1. The diff

Session start: `SESSION_REPORT.md` was moved to `reports/session-12.md` and that
move was committed by itself as **`b9f58e2`**, per `CLAUDE.md`.

```
 DEMO_VERIFICATION.md         | 167 ++++++++++++++++++++++++++++++++++++++++---
 config/skills.yaml           |  11 ++-
 docs/LESSONS.md              |  69 +++++++++++++++++-
 services/mcp-canvas/app.py   |  35 ++++++++-
 services/orchestrator/app.py |   6 ++
 tests/test_skills.py         |  89 ++++++++++++++++++-----
 tests/test_tool_results.py   |  48 +++++++++++++
 7 files changed, 392 insertions(+), 33 deletions(-)
```

Plus this file. **Every path is inside the brief's permitted list**, and
`apps/` is untouched — §3.3 says why the per-role hiding option was declined.
The forbidden paths are clean, proven rather than asserted:

```
$ git diff --exit-code --stat services/audit/ services/mcp-colleague/ \
      services/mcp-kuali/ services/mcp-labor/ services/orchestrator/prompts.py \
      services/orchestrator/grounding.py apps/ scripts/
UNCHANGED: audit, mcp-colleague, mcp-kuali, mcp-labor, prompts.py, grounding.py, apps, scripts
```

No seed change was made and none was needed.

---

## 2. Item 1 — the rollup totals

Session 12 §6.4 proposed this and was not permitted to build it. It is the sixth
application of "let the tool compute it", and like the five before it, it held.

### 2.1 What was built

`services/mcp-canvas/app.py` only. One new model, and the tool's return type
changes from a bare list to it:

```python
class ProgramEngagementRollup(BaseModel):
    total_sections: int
    total_enrollment: int
    total_missing_submissions: int
    programs: list[ProgramEngagement]
```

Each total is summed from the rows just built, not from a second query, so a
total and the table beside it cannot disagree whatever the `program_code` filter
did:

```python
        return ProgramEngagementRollup(
            total_sections=sum(program.sections for program in rollup),
            total_enrollment=sum(program.enrollment for program in rollup),
            total_missing_submissions=sum(program.missing_submissions for program in rollup),
            programs=rollup,
        )
```

The docstring is extended the way `get_my_advisees`' was — the totals are
authoritative and must not be re-derived:

> "…programs holds one row per program; total_sections, total_enrollment and
> total_missing_submissions are the totals across exactly those rows. Those
> three totals are authoritative: state them as this result gives them, and
> never re-derive one by adding the rows up."

**There is deliberately no total for `pct_logged_in_this_week`**, and the class
docstring says so: a share is not summable, and a field that looked like one
would invite the error the class exists to prevent.

### 2.2 The test

`tests/test_tool_results.py::test_the_engagement_rollup_states_its_own_cross_program_totals`.
One test, asserting each of the three totals equals the sum of that column over
the rows shipped beside it, plus a non-zero check so a rollup of an empty
catalog cannot pass by arithmetic.

### 2.3 The measurement — step 5c ×5, rows 7626–7660

Five fresh conversations as kim through the gateway, toggle off. Ground truth
recomputed from `data/canvas.db` rather than quoted from seed output:

```
program    sections  enroll pct_active  missing
BUS-BS            4      22       63.6       12
CS-BS             3      20       95.0       16
CYB-BS            5      43       86.0       28
DAT-MS            3      29       89.7       24
HIM-BS            3      31       77.4       22
IS-MS             2      20       80.0       10
TOTAL            20     165          —      112
```

| Measure | Target | Result |
|---|---|---|
| Cross-program total stated verbatim from the tool | 5 of 5 | **5 of 5** ✔ (112, and 20 sections / 165 enrolled with it) |
| All 18 rollup cells exact | 5 of 5 | **5 of 5** ✔ |
| The 6 missing-submission counts exact | 5 of 5 | **5 of 5** ✔ |
| Guard declines | 0 | **0** ✔ |
| Model calls with zero cache hits | 0 | **0** ✔ (10 calls, minimum hit tokens 896) |

Run 1's opening sentence, and four of the five open the same way:

> Across 20 sections and 165 enrolled students, 112 submissions are missing this
> week. [canvas]

Median latency 11.7s. **Five guard fires and five regenerations, zero
declines** — every first attempt cited `[colleague]` (once `[kuali]`) for a
canvas-only request, the five-session-old marker misfire, and every regeneration
came back clean and correctly cited. That rate is higher than the certification
pass's, and it is worth recording: on this beat specifically, the first draft
gets the marker wrong nearly every time and the guard catches it every time.

One wart, not a spec violation: run 3 opens "112 of 165 total submissions are
missing", which reads 165 as a submission count when it is an enrollment. Both
figures are transcribed correctly from the tool; the sentence joins them wrongly.

---

## 3. Item 2 — the skill, scoped by the registry

### 3.1 What changed

`config/skills.yaml`, one line, with the reason above it in the file:

```yaml
    roles: [advisor, dean, adjunct]
```

`faculty` is gone. noor is the only faculty persona and demo moment 5 is her
beat, so the combination Session 12 measured as worse — the skill active on
moment 5 — is now unreachable by registry rather than by documentation.

### 3.2 The tests

`tests/test_skills.py` goes from three tests to four. The unauthorized case now
comes in two halves, and the brief allowed either replacing or joining the old
one; joining is stronger because the two fail differently:

- **`test_a_real_persona_whose_role_the_skill_excludes_is_refused`** — noor's
  own token, refused with `reason: "not_authorized"`. This is the test that
  fails if anyone grants the role back.
- **`test_a_role_the_registry_has_never_heard_of_is_refused`** — the minted
  `registrar` token Session 12 wrote, kept unchanged. This is the test that
  fails if `resolve` ever defaults an unrecognised role to permitted.

Proven live over the surface path, not only in the suite. noor through the
gateway — the same hop the Chainlit apps make:

```
$ curl -s -X POST localhost:8000/chat -H "Authorization: Bearer $NOOR" \
    -d '{"message":"How is my CYB-310 section doing this week?","history":[],
         "active_skills":["plain_language"]}'
{"reply": "The “plain_language” mode is not available to your role, so I
 have not applied it. Ask again without it and I will answer normally.",
 "tools_used": []}
```

and the row it wrote, which is amber because of item 3:

```
7600  orchestrator  skill_refused  noor  ['faculty']
      {"skill": "plain_language", "reason": "not_authorized",
       "requested": ["plain_language"], "decision": "refused", "latency_ms": 0.0}
```

### 3.3 The toggle in ui-advisor — and why `apps/` was not touched

**The switch still renders for noor, and that is the right answer, not a
shortfall.** The brief allowed per-role hiding "if Chainlit allows it cheaply".
It is not a question of cheapness: the surfaces hold no roles at all. They never
decode the token — `harness_chat.py`'s own docstring says a surface "decides
nothing. No role checks, no tool lists, no model calls" — so hiding the switch
per role would mean teaching a Chainlit app who holds what, which is an
entitlement decision in a surface and exactly what `CLAUDE.md`'s third hard rule
forbids. Flipping the switch as noor produces the refusal above and no answer.
**The refusal path is the guarantee**, and `DEMO_VERIFICATION.md` now says so in
those words.

### 3.4 The document

`DEMO_VERIFICATION.md`'s optional-beat section: constraint 2 was "do not run
demo moment 5 with the toggle on" and is now "demo moment 5 cannot be run with
the toggle on, because noor cannot activate the skill at all". Session 12's
measured numbers are kept, one sentence, as the reason the role was removed.

---

## 4. Item 3 — a refused skill is amber

One key in one audit call, `services/orchestrator/app.py`:

```python
                        "decision": "refused",
```

`services/audit/viewer.html` colours a row by `detail.decision` and was not
touched. One assertion was added to the existing unknown-skill test. The
certification's appended beat confirms it end to end, including the viewer rule
read rather than assumed — `rowClass` finds `"refused"` and paints
`--refused: #fbbf24`; without the key the row falls through to the green
default.

---

## 5. Item 4 — the attribution measurement, no fix permitted

**Deviation, and it is the only one this session: a matched toggle-off control
arm was run that the brief did not ask for.** The brief said to score step 2b ×5
"beside Session 12's toggle-off step 2 runs", but Session 12 never scored those
runs for attribution — it scored them for figures, register and latency, and its
attribution observation (W2) was a single reply from the certification pass.
Comparing five scored runs against one unscored anecdote would have produced a
number with nothing to sit beside. So five toggle-off runs were added, scored
identically. This is measurement, not a fix, and it is what makes the comparison
mean anything.

Kim's step-2 question, ten runs. Toggle off rows 7661–7752; toggle on rows
7753–7803. Each reply scored on whether every marker names the server whose tool
supplied that figure — `[colleague]` for headcount, average GPA and the
quiet-over-ten-days share; `[canvas]` for sections, weekly login rate, missing
submissions and the three totals.

| Attribution | Toggle off | Toggle on |
|---|---|---|
| Both servers cited, every marker correct | **2 of 5** (runs 2, 5) | **2 of 5** (runs 1, 5) |
| Both servers' figures, all signed with one marker | **2 of 5** (runs 3, 4) | **2 of 5** (runs 2, 4) |
| Canvas-only content, correctly signed | 1 of 5 (run 1) | 1 of 5 (run 3) |
| Guard fires / declines | 1 / 0 | 1 / 0 |
| `active_skills` on `answer_returned` | `[]` ×5 | `["plain_language"]` ×5 |
| Model calls with zero cache hits | 0 (min 896) | 0 (min 896) |
| Median latency | 15.5s | **11.5s** |

**The distributions are identical, so the skill does not measurably worsen
attribution and the brief's conditional does not fire.** Session 12's W2 was one
draw of a coin that lands the same way with the skill off. The finding worth
keeping is the rate: on a question that joins two systems, two replies in five
sign both systems' figures with one marker, in both arms. That is entry 5's
third blind spot — the guard cannot judge *which* marker is right when two
servers ran — measured rather than assumed.

Two observations, neither strong enough to call a finding:

- The toggle-on arm produced one invented figure: "28.7% of its assignments are
  missing (12 out of what appears to be about 42 total)". No tool returns 42 or
  28.7%. One instance in ten replies; the toggle-off arm produced none.
- The toggle-**off** arm made more than twice as many tool calls (76 `tool_call`
  rows against 35), almost all of them `get_section_engagement` with section ids
  the model invented and the server refused. That cuts against a simple reading
  of Session 12's "the skill displaces fetching": on this beat the skill-off arm
  fetched more and produced worse prose for it.

Nothing was changed in response. The measurement was the deliverable, and it is
recorded in `docs/LESSONS.md` entry 13 and `DEMO_VERIFICATION.md` — including a
proposed patter line, which is to say out loud that the register changed and the
provenance accuracy did not.

---

## 6. Item 5 — the final certification

One pass by the demo-verifier agent, **rows 7804–7901**, 98 rows,
2026-08-10 00:49:46–00:56:57Z. Steps 1–10 with no `active_skills` field at all,
plus step 2b with `["plain_language"]`, plus the appended amber-refusal check
after step 10. Driven through the gateway with real persona tokens; step 4 ran
`./scripts/demo_bypass.sh` unmodified; step 5b carried step 5a's rendered prose
back as client-held history. Every figure recomputed from `data/*.db`. The
verifier changed nothing.

**It scored 12 items, not 14.** The brief said "steps 1–10 plus 2b plus the
appended check", which is 12 if step 5's three sub-asks count as one beat and 14
if they count as three. The verifier scored 12 and broke 5a/5b/5c out inside the
one entry; both readings describe the same work, and 5a, 5b and 5c all passed.

### 6.1 Result — 9 of 12

| Beat | Verdict |
|---|---|
| 1 | PASS — 25 / 9 / 8 exact, group membership right |
| **2** | **FAIL** — a derived ratio wrong, and three paragraphs of scratchpad before the answer |
| **2b** | **FAIL** — register clearly better, row 7828 carries the skill, and it repeats step 2's ratio error |
| 3 | PASS — gate refusal row 7830; all 36 occupation cells exact |
| 4 | PASS — `tools that actually ran: none`; mcp-colleague refusal row 7837 verbatim |
| 5a | PASS |
| 5b | PASS — the tool was called and refused, spec sentence verbatim at the tool layer (row 7846) |
| **5c** | **PASS — the beat Session 12 failed** |
| 6 | PASS |
| **7** | **FAIL** — "0 of 5" for an occupation with 6 skills, named in the same line |
| 8 | PASS — six distinct `get_course_outcomes` calls (7881–7886) before any catalog-wide claim |
| 9 | PASS |
| 10 | PASS — 401 at all six token-validating services independently |
| **amber check** | **PASS** — row 7895 carries `"reason": "unknown"` and `"decision": "refused"` |

Standing checks, all green:

| Check | Result |
|---|---|
| Prompt cache | **23** model calls with telemetry, minimum `prompt_cache_hit_tokens` **896**, **zero** calls with zero hits |
| Four spec-fixed refusal strings, verbatim at the tool layer | **All four** (rows 7837, 7846, 7897, 7898, 7899, 7900) |
| Faculty/dean asymmetry | Proven on an **identical `args_hash 8dcd893de78e`** — row 7900 noor refused, row 7901 kim served |
| Dropped audit events in the window | **Zero** |
| `tools_used ⊆ tools_offered` | Holds on **11 of 11** `answer_returned` rows; `unoffered_calls` present and empty on every one |
| Guard ledger | **2 fires, 2 regenerations, 0 declines** (7822, 7852) |
| `active_skills` discipline | Row 7828 `["plain_language"]`; the other **ten** `[]` |
| Every id, code and figure recomputed | Three stated figures wrong across the pass, all three named below |

### 6.2 The fix, on the record

Step 5c's opening sentence, which is the whole point of item 1:

> "Across 20 sections and 165 enrolled students, 112 submissions are missing
> this week. [canvas]"

Session 12's certification produced "78 missing submissions" on this beat. All
18 per-program cells and all 6 missing counts were exact in both passes; the
difference is the one number that is now a field rather than a sum.

### 6.3 The three failures, and whose they are

**Every one is a quantity no tool states, in a beat this session did not touch.**
The brief's rule is that such a failure is reported against its session of
origin, and the no-fixing-after-measurement rule applied to all three.

- **Steps 2 and 2b — the same derived ratio.** Both say CS-BS has "the highest
  missing-to-enrollment ratio of any program". Recomputed independently:

  ```
  DAT-MS    24/ 29 = 0.828
  CS-BS     16/ 20 = 0.800
  ```

  DAT-MS holds it. Every figure either reply takes *from* a tool is exact. **The
  skill neither caused it nor caught it** — step 2, the same question with the
  toggle off, makes the identical error — which is a second, independent
  confirmation of §5's result from inside the certification.
- **Step 7 — one wrong denominator.** "0 of 5" for Financial Analysts, whose
  missing-skill list in the same line names six. Recomputed from `data/labor.db`:
  Financial Analysts (13-2051) carries **6** skills. This is Session 9 finding
  9.2 and Session 11 §5.3's second instance, same beat, same shape.
- **The scratchpad leak, on 3 of 12 beats** (2, 7, 8), all kim's, all multi-tool
  syntheses. Session 12 recorded it as W1 and Session 9 as the narration leak.
  This pass scored it as a failure on step 2 rather than as a wart — a stricter
  reading of the same behaviour, not a regression. Worth noting: **step 2b, the
  same question with the skill on, produced no preamble at all.** Suppressing
  throat-clearing is the one thing the skill reliably does.

### 6.4 Why the fallback was not executed

The brief pre-authorized one halt: *if item 1's fix fails its ×5 or the
certification fails 5c again, report and halt.* Item 1 passed 5 of 5 and step 5c
passed. Neither clause fired, so the work was committed. **The pass was not
re-run**, for Session 12 §6.3's reason: the rule against fixing after
measurement is worth nothing if measurement can be repeated until it agrees.

### 6.5 The verifier's proposals, recorded and not applied

- Add `missing_submissions_per_student: float` to each `ProgramEngagement` row —
  the exact quantity the model got wrong twice in one pass, on the beat that
  opens the executive demo.
- Add `skill_count: int` to the occupation payload in `services/mcp-labor` —
  step 7's "n of N", where N is a length the model counts itself.
- **Seed:** BUS-201-A holds 2 students and BUS-201-B holds 1, so kim serving the
  section noor was refused pays off with a two-row roster. SPEC §5 asks for
  BUS-201-B to be "visibly not" healthy and at n=1 that is one person, not a
  signal. Raising both to 12–18 students would fix it and would move the
  20 / 165 / 112 totals pinned throughout `DEMO_VERIFICATION.md`, so it is a
  re-seed plus a recomputation. **Not applied.**

All three are the same lesson the fix that worked came from, aimed one step
further.

---

## 7. The documents

**`docs/LESSONS.md` entry 4** gains the fifth and sixth tally marks in its table
(Session 12's membership lists and Session 13's rollup totals) and a short
paragraph stating the score plainly: six applications, six holds, no exceptions,
and the sixth was chosen because the fifth worked. **Entry 9** gains the rollup
instance in full. **Entry 13** gains two things the brief asked for: the
registry-enforcement outcome, written as a general lesson — *a measured
behavioural risk should end up in the same registry that governs everything
else, not in a footnote about how to run the demo* — including why the two
surfaces were left alone; and the attribution finding, reported as no effect,
with the two-in-five provenance rate as the number the MVP should design
against.

**`DEMO_VERIFICATION.md`** gains a Session 13 section as the current record
(Session 12's is demoted to superseded), and its optional-beat section gains the
rewritten constraint 2 and the patter line.

---

## 8. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | `get_program_engagement_rollup` returns the three totals from the rows it ships; docstring extended; one test; no seed change; restart; step 5c ×5 with the total verbatim and all 18 cells exact | **PASS on every clause.** 5 of 5 verbatim, 5 of 5 with all 18 cells and all 6 missing counts exact. §2 |
| 2 | `plain_language`'s roles become `[advisor, dean, adjunct]`; `test_skills.py` updated; `DEMO_VERIFICATION.md` constraint 2 rewritten; the toggle verified for noor in ui-advisor | **PASS.** The unauthorized case now has two halves rather than one; `apps/` untouched and §3.3 says why the refusal path is the guarantee |
| 3 | `skill_refused` gains `"decision": "refused"`; no change to `services/audit/`; one assertion added | **PASS.** §4, and the certification's appended beat confirms it live |
| 4 | Step 2b ×5 scored for attribution beside Session 12's toggle-off runs; report the comparison; no fix | **PASS, with one deviation** — a matched toggle-off control arm was added, because Session 12 never scored its runs for attribution. §5. The skill's effect is nil, so the conditional output did not fire; the finding is recorded anyway |
| 5 | One full demo-verifier pass, steps 1–10 plus 2b, toggle off except 2b, standing checks in full, plus the appended amber check | **RUN. 9 of 12.** All standing checks green; 5c passes; the three failures are older than this session and in beats it did not touch. §6 |
| — | FALLBACK if item 1's ×5 fails or the certification fails 5c again | **NOT TRIGGERED.** Neither clause fired. §6.4 |
| 6 | LESSONS entry 4's sixth tally mark; entry 13's registry outcome and attribution finding; the commit | **PASS.** §7 |
| — | `pytest` green, 139+ | **PASS — 139 passed.** §9 |
| — | Certification 14/14 | **NOT MET — 9 of 12.** Neither the 12- nor the 14-item reading is satisfied. §6.3 states what failed and why it was not fixed |
| — | Diff confined to `services/mcp-canvas/app.py`, `config/skills.yaml`, `services/orchestrator/app.py`, `apps/` (only if per-role hiding is done), `tests/`, `docs/LESSONS.md`, `DEMO_VERIFICATION.md`, `SESSION_REPORT.md` | **PASS.** Seven files plus this one, all inside the list; `apps/` untouched. §1 |

---

## 9. Evidence — the suite and the pre-demo check

```
$ uv run pytest tests/ -q
139 passed in 52.00s
```

137 before this session, plus one rollup-totals test and one persona-based
unauthorized-skill test. No test was removed or weakened, and no check anywhere
was loosened to make one pass.

The pre-demo check, run **after** the suite as `CLAUDE.md` instructs. Three
drops in the half-hour view, and each lands about a third of a second after the
disruptive test stops the audit container on purpose — one per suite run:

```
$ docker compose logs --since 30m --timestamps 2>&1 | grep -E "dropped|Shutting down"
audit-1     2026-08-10T00:38:34.943Z INFO:     Shutting down
gateway-1   2026-08-10T00:38:35.268Z audit event 'auth_failed' dropped ...
audit-1     2026-08-10T00:40:02.996Z INFO:     Shutting down
gateway-1   2026-08-10T00:40:03.329Z audit event 'auth_failed' dropped ...
audit-1     2026-08-10T01:03:24.442Z INFO:     Shutting down
gateway-1   2026-08-10T01:03:24.749Z audit event 'auth_failed' dropped ...
```

**The certification pass ran 00:49:46–00:56:57, entirely between the second and
third of those**, and the verifier independently confirmed zero drops inside its
own window with a `--since` scoped to it. The receipts demo moment 9 points at
are complete.

### Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-12.md && git commit          # b9f58e2

# items 1, 2 and 3 — all code changes before any measurement
docker compose restart mcp-canvas orchestrator
uv run pytest tests/ -q                                               # 139 passed

# item 1's measurement
uv run python truth.py                                                # 20 / 165 / 112
uv run --with httpx python warm.py                                    # rows 7602-7625
uv run --with httpx python ask.py kim "How's engagement across all programs this week?" 5 5c.json
                                                                      # rows 7626-7660

# item 4 — the attribution arms
uv run --with httpx python ask.py kim "Which students seem to be struggling this term?" 5 step2-off.json
                                                                      # rows 7661-7752
uv run --with httpx python ask.py kim "Which students seem to be struggling this term?" 5 step2-on.json '["plain_language"]'
                                                                      # rows 7753-7803

# item 5 — the certification
# the demo-verifier agent, steps 1-10 + 2b + the appended amber check  # rows 7804-7901

# acceptance
uv run pytest tests/ -q                                               # 139 passed
docker compose logs --since 30m 2>&1 | grep dropped                   # the disruptive test, above
```

Scratchpad helpers (`ask.py`, `warm.py`, `truth.py`, `truth2.py`, `score5c.py`)
and the run transcripts are throwaway; nothing in the repository depends on
them. The verifier's own artefacts — one request/reply/raw triple per beat, the
98-row audit window dump, its independent ground-truth recomputation and its
driver script — are beside them under `cert/`.

---

## 10. Open questions

1. **The remaining arithmetic defects are three tool fields away**, and the
   pattern that would close them has now worked six times for six. §6.5 names
   two of them precisely: a per-student missing-submission ratio on the rollup
   rows, and a skill count on the occupation payload. Neither was in scope and
   both are one short session's work.

2. **The scratchpad leak is now the largest presentation defect**, on 3 of 12
   beats and on the two the room reads off a projector. It has been recorded as
   a wart since Session 9 and never measured or acted on. The one datum worth
   having: the plain-language skill suppresses it completely, which suggests it
   is an output-discipline gap rather than anything about tools — and suggests a
   `surface-default` skill, from entry 13's taxonomy, would fix it without
   anyone touching a switch.

3. **Two replies in five sign both servers' figures with one marker** (§5).
   That is the single largest honest weakness in the synthesis claim, it is
   invisible to the groundedness guard by design, and no configuration moves it.
   Entry 5 names the one safe correction — rewriting markers when exactly one
   server ran — and Session 11 measured what it costs.

4. **BUS-201's section sizes** (§6.5). The dean half of demo moment 5 pays off
   with a two-row roster. It is a seed change with a recomputation attached.

5. **Everything in this session is committed**; the commit follows this report.
