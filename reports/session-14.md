# SESSION_REPORT — harness-poc Session 14

The final session. Two tool fields were built and both were measured. **Both
measurements failed their acceptance criteria, so the pre-authorized fallback
fired: I reported and halted. The closing certification was not run, no
document was updated, and nothing was committed.**

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

## The headline, in five sentences

**The two fields work exactly as designed, and the pattern still did not hold
for the seventh and eighth time.** Every value either field ships was
transcribed correctly into every reply — all thirty per-program ratios across
five runs, and all forty-one "of N" denominators across five runs, including the
Financial Analysts denominator that failed Session 13's certification.

**What failed is one step further out than the fields reach.** Step 2 stated two
*ordinal* claims about the new ratio that contradict it — "HIM-BS … 0.71 missing
submissions per student, second-highest" when it is third, and "BUS-BS … the
lowest missing-per-student ratio" when IS-MS is lower — in a reply whose own
table prints all six correct values. Step 7 stated four wrong *numerators* over
correct denominators, twice arguing with itself on screen while doing it.

**The score is 3 of 5 clean on step 2 and 2 of 5 clean on step 7.** The brief's
acceptance was "zero derived-figure errors anywhere in the replies" and "zero
wrong tallies of any kind", so both fail, and the fallback is unambiguous:
*report and halt — no reversion (the fields are additive), no re-run.*

**The fields are still in the working tree, uncommitted, and the suite is green
at 141.** §7 sets out the three things I did not do and why, and §8 asks the one
question I cannot answer without you.

---

## 1. What was done, and what was not

| Brief item | Status |
|---|---|
| 1 — `missing_per_student` on each rollup row, docstring, one test | **Built and passing.** §2 |
| 2 — `skill_count` on the occupation payload, docstring, one test | **Built and passing.** §3 |
| 3 — restart, step 2 ×5 and step 7 ×5, toggle off | **Measured. Both fail their acceptance.** §4, §5 |
| 4 — the closing certification | **NOT RUN.** The fallback fired first. §7 |
| 5 — LESSONS 4 and 9, DEMO_VERIFICATION, the commit | **NOT DONE.** Conditioned on success. §7 |
| FALLBACK — if either measurement shows a derived-figure error, report and halt | **EXECUTED.** §6 |

Session start: `SESSION_REPORT.md` was moved to `reports/session-13.md` and that
move was committed by itself as **`bc5b715`**, per `CLAUDE.md`. That is the only
commit this session.

The working tree, unstaged:

```
$ git status --porcelain
 M services/mcp-canvas/app.py
 M services/mcp-labor/app.py
 M tests/test_tool_results.py

$ git diff --stat
 services/mcp-canvas/app.py | 28 +++++++++++++++-
 services/mcp-labor/app.py  | 35 +++++++++++++-------
 tests/test_tool_results.py | 82 ++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 133 insertions(+), 12 deletions(-)
```

Three files, all inside the brief's permitted list. Nothing in
`services/audit/`, `mcp-colleague/`, `mcp-kuali/`, `prompts.py`,
`grounding.py`, `config/`, `apps/` or `scripts/` was touched — the diff above is
the whole of it. `docs/LESSONS.md`, `DEMO_VERIFICATION.md` and this file were in
the permitted list too; the first two are unchanged because item 5 never became
due.

---

## 2. Item 1 — `missing_per_student`

`services/mcp-canvas/app.py` only. `ProgramEngagement` gains one field, computed
from the two fields beside it in the same row:

```python
def per_student(missing: int, enrollment: int) -> float:
    """Missing submissions per enrolled student, to three decimal places. …"""
    if not enrollment:
        return 0.0
    return round(missing / enrollment, 3)
```

The division is named and defined once so the tool and the test agree on what
the number means, and a program with no enrolled students returns `0.0` rather
than being the one nullable field in the row.

The class gains a docstring in the established form — what the field is, and the
sentence from the record that explains why it exists:

> `missing_per_student` is `missing_submissions / enrollment` for this row and
> nothing else. … Session 13's certification pass called CS-BS "the highest
> missing-to-enrollment ratio of any program" in both arms of the same beat,
> where CS-BS is 16/20 = 0.800 and DAT-MS is 24/29 = 0.828.

The tool docstring gains the instruction, appended to the totals sentence
already there:

> Each row's `missing_per_student` is that program's missing submissions per
> enrolled student: any comparison or ranking of programs by missing-work burden
> comes from this field, and a ratio must never be re-derived from the other
> columns.

**The test.**
`tests/test_tool_results.py::test_every_rollup_row_states_its_own_missing_work_rate`
— one test, asserting on every row that the field equals
`round(missing_submissions / enrollment, 3)` for the two fields shipped beside
it, plus a non-zero check so a catalog with no missing work could not pass by
arithmetic.

---

## 3. Item 2 — `skill_count`

`services/mcp-labor/app.py` only. `Occupation` gains `skill_count: int`, and
both tools now build the model through one helper so the count cannot be taken
from anywhere but the list it ships with:

```python
def occupation_from(row: sqlite3.Row) -> Occupation:
    """One occupation row, with skill_count taken from the list it ships with."""
    skills = skills_for(row["soc_code"])
    return Occupation(
        soc_code=row["soc_code"], title=row["title"], growth_pct=row["growth_pct"],
        median_wage=row["median_wage"], skill_count=len(skills), skills=skills,
    )
```

Both `list_occupations` and `get_occupation` docstrings gain the same sentence:

> `skill_count` is how many skills it has: every "n of N" denominator about an
> occupation's skills is its `skill_count`, and the list is never to be counted.

**The test.**
`tests/test_tool_results.py::test_every_occupation_states_how_many_skills_it_holds`
— `skill_count == len(skills)` on every one of the twelve occupations, not just
the four the demo headline names, because the misses have always been in the
secondary ones.

**Both servers were restarted before any measurement**, as the brief required:

```
$ docker compose restart mcp-canvas mcp-labor
 Container harness-poc-mcp-labor-1 Started
 Container harness-poc-mcp-canvas-1 Started
```

---

## 4. The step 2 measurement — 3 of 5 clean, acceptance FAILED

Five fresh conversations as kim through the gateway, no `active_skills` field,
**audit rows 8313–8352**, 2026-08-10 01:30:27–01:31:53Z. Question: *"Which
students seem to be struggling this term?"* Ground truth recomputed from
`data/canvas.db` and `data/colleague.db` rather than quoted from any earlier
report:

```
program  sections  enroll  pct_active  missing  missing_per_student
BUS-BS          4      22        63.6       12                0.545
CS-BS           3      20        95.0       16                0.800
CYB-BS          5      43        86.0       28                0.651
DAT-MS          3      29        89.7       24                0.828
HIM-BS          3      31        77.4       22                0.710
IS-MS           2      20        80.0       10                0.500
TOTAL          20     165           —      112

ranked by missing_per_student:
  DAT-MS 0.828 > CS-BS 0.800 > HIM-BS 0.710 > CYB-BS 0.651 > BUS-BS 0.545 > IS-MS 0.500
```

### 4.1 What held

| Measure | Target | Result |
|---|---|---|
| DAT-MS named as the highest missing-work burden wherever a leader is named | 5 of 5 | **5 of 5** ✔ |
| Every `missing_per_student` value stated is the field's value | every instance | **30 of 30 exact** ✔ |
| Every figure taken from a tool (enrollment, missing, login %, GPA, quiet %, the three totals) | exact | **exact in all five runs** ✔ |
| Any individual student named | 0 | **0** ✔ |
| Guard declines | 0 | **0** ✔ (one fire, one regeneration, row 8344) |
| Model calls with zero cache hits | 0 | **0** ✔ (10 calls, minimum hit tokens 896) |
| `active_skills` on `answer_returned` | `[]` ×5 | **`[]` ×5** ✔ |

Run 5's opening, which is what the field was built to produce:

> Highest missing-work burden (missing submissions per enrolled student):
> 1. **DAT-MS (Data Analytics, MS)** — 0.83 per student, 24 missing across 29
>    enrolled [canvas]
> 2. **CS-BS (Computer Science, BS)** — 0.80 per student, 16 missing across 20
>    enrolled [canvas]
> 3. **HIM-BS (Health Information Management, BS)** — 0.71 per student, 22
>    missing across 31 enrolled [canvas]

### 4.2 What failed — two ordinal claims that contradict the field

**Run 1 (row 8319) — "second-highest" about the third-highest, twice over.**

> ### 3. Health Information Management, BS (HIM-BS)
> - 0.71 missing submissions per student, **second-highest** [canvas].

HIM-BS at 0.710 is third. The same reply then says, two sections later:

> ### 4. Computer Science, BS (CS-BS)
> - 0.80 missing submissions per student, **the second-highest missing-work
>   burden** [canvas].

CS-BS is second. So the reply awards the same rank twice and one of them is
wrong, on the projector, with both correct values printed above the claims.

**Run 4 (row 8340) — "the lowest" about the second-lowest.**

> BUS-BS has a quarter of its students quiet for over 10 days **despite having
> the lowest missing-per-student ratio**

IS-MS is lower, at 0.500 against BUS-BS's 0.545 — and run 4's own table, four
lines above, prints all six values to three decimal places and every one of them
is exact:

> | **DAT-MS** | 0.828 | 24 | 29 | 89.7% |
> | **CS-BS** | 0.800 | 16 | 20 | 95.0% |
> | **HIM-BS** | 0.710 | 22 | 31 | 77.4% |
> | **CYB-BS** | 0.651 | 28 | 43 | 86.0% |
> | BUS-BS | 0.545 | 12 | 22 | 63.6% |
> | IS-MS | 0.500 | 10 | 20 | 80.0% |

Runs 2, 3 and 5 are clean on every figure and every ranking. Run 3 prints the
full six-program ranking in the right order with every quotient exact.

**Verdict against the brief's wording** — *"any ranking or superlative about
missing-work burden is consistent with `missing_per_student`; zero derived-figure
errors anywhere in the replies"* — **FAILED, 3 of 5.**

Median latency 17.9s.

### 4.3 One wart, recorded not scored

Runs 1 and 2 both call BUS-BS's 0.545 "middle of the pack" and "middling" when
it is fifth of six. That is a vague characterisation rather than a stated figure
or an explicit rank, so I did not score it as an error; it points the same way as
the two that are.

---

## 5. The step 7 measurement — denominators 5 of 5, tallies 2 of 5, acceptance FAILED

Five fresh conversations as kim, **audit rows 8353–8421**, 01:33:15–01:34:39Z.
Question: *"Which fast-growing occupations would a Cybersecurity BS graduate
qualify for?"* Ground truth recomputed by joining `data/kuali.db`'s CYB-BS
outcome skill tags (16 distinct skills) against `data/labor.db`'s occupation
skills:

```
occupation                                    growth    wage      covered / skill_count
AI/ML Engineers                                35.2  $136,620       0 of 7
Cloud Infrastructure Architects                33.8  $130,390       3 of 7
Information Security Analysts                  32.7  $120,360       8 of 8
Data Scientists                                28.4  $108,020       0 of 7
Medical and Health Services Managers           24.1  $110,680       1 of 5
Network and Computer Systems Administrators    21.5  $ 95,360       3 of 6
Software Developers                            17.9  $132,270       2 of 6
Computer and Information Systems Managers      15.4  $169,510       1 of 5
Management Analysts                            10.6  $ 99,410       0 of 5
Computer Systems Analysts                      10.4  $103,800       2 of 5
Medical Records Specialists                     8.6  $ 48,780       1 of 5
Financial Analysts                              8.2  $ 99,890       0 of 6
```

### 5.1 The denominators — the half that worked, completely

| Measure | Target | Result |
|---|---|---|
| Every "of N" matches `skill_count` — headline four and every secondary occupation | 5 of 5 runs | **5 of 5** ✔ |
| Total denominators stated across the five runs | — | **41, every one exact** (3 + 6 + 12 + 8 + 12) |
| Financial Analysts stated as "of 6" wherever it appears | — | **2 of 2** ✔ (runs 3 and 5) |
| Every growth rate and median wage | exact | **exact in all five runs** ✔ |
| The CYB-BS skill list, where printed | exact | **2 of 2** ✔ (16 skills, runs 3 and 5) |
| Guard fires / declines | 0 | **0 / 0** ✔ |
| Model calls with zero cache hits | 0 | **0** ✔ (10 calls, minimum 896) |
| `active_skills` on `answer_returned` | `[]` ×5 | **`[]` ×5** ✔ |

**Session 13's exact failure is gone.** That pass said "0 of 5" for Financial
Analysts on a line naming six skills. Run 3 of this measurement says:

> **Financial Analysts** (8.2% growth, $99,890): **0 of 6 skills covered.**
> [kuali][labor]

Run 3 gets all twelve occupations right — twelve denominators, twelve
numerators, twelve growth rates, twelve wages, no error anywhere.

### 5.2 The numerators — four wrong tallies in three runs

**Run 2 (row 8379)** states a tally, doubts it mid-sentence, and rewrites it in
front of the reader:

> **Network and Computer Systems Administrators** (21.5% growth, $95,360):
> **4 of 6 skills covered**. Covers: network engineering, systems
> administration, technical documentation, cloud architecture (not covered).
> Missing: cloud architecture, containerization, infrastructure automation —
> **wait, let me recheck that.** Covers: network engineering, systems
> administration, technical documentation.

True figure 3 of 6. The denominator is right; the count of covered skills is not,
and the correction is left on screen.

**Run 4 (row 8412)** invents the same coverage twice, by putting one CYB-BS skill
into two occupations that do not require it:

> **AI/ML Engineers** (35.2% growth, $136,620): **1 of 7 skills covered**
> - Covered: API design.

AI/ML Engineers' seven skills do not include API design. True figure 0 of 7.

> **Network and Computer Systems Administrators** (21.5% growth, $95,360):
> **4 of 6 skills covered**
> - Covered: network engineering, systems administration, technical
>   documentation, API design.

Neither does that occupation's six. True figure 3 of 6, and the reply repeats
"4 of 6" in its closing summary, which is the line the room reads.

**Run 5 (row 8420)** states a tally that its own bullet contradicts on the next
line:

> **Cloud Infrastructure Architects** (33.8% growth, $130,390) — **5 of 7 skills
> covered**
> - Covered: API design, network engineering, systems administration,
>   infrastructure automation (missing), cloud architecture (missing),
>   containerization (missing), distributed systems (missing)
> - Missing: infrastructure automation, cloud architecture, containerization,
>   distributed systems

True figure 3 of 7. The "Covered" line lists the four missing skills as covered
and annotates each as missing. The summary repeats the wrong figure — *"The only
other fast-growing occupation with substantial coverage is Cloud Infrastructure
Architects at 5 of 7 skills"* — and the same run also says Software Developers is
"3 of 6" above a covered-list of two (true figure 2 of 6).

Runs 1 and 3 are clean on every tally.

**Verdict against the brief's wording** — *"every denominator … matches
`skill_count` exactly; zero wrong tallies of any kind"* — the denominator clause
**passed 5 of 5**; the tally clause **FAILED, 2 of 5**.

Median latency 17.3s.

---

## 6. Why the fallback fired, and what it stopped

The brief pre-authorized exactly one halt:

> **FALLBACK, pre-authorized:** if either measurement in item 3 shows a
> derived-figure error, or the certification finds any wrong figure, report and
> halt — no reversion (the fields are additive), no re-run.

Both measurements show derived-figure errors, on the plain reading and on any
reading I can construct. So:

- **No fix was made after measurement began.** Nothing in the repository changed
  after the first timed request went out at 01:30:27Z.
- **No measurement was re-run.** Session 12 §6.3 and Session 13 §6.4 both say
  why, and it applies to a failing measurement as much as to a failing
  certification: the rule against fixing after measurement is worth nothing if
  measurement can be repeated until it agrees.
- **No reversion.** The fields are additive and are still in the working tree.
- **The certification was not run.** It is item 4, and item 3's failure comes
  first in the brief's own ordering.
- **Item 5 was not done.** It is conditioned on success — no LESSONS entry, no
  `DEMO_VERIFICATION.md` record, no commit.

**What I did not decide for you: whether these two changes ship.** They are
uncommitted. §8 asks.

---

## 7. What this measurement actually shows, stated carefully

This matters more than the pass/fail, because it is the first time in nine
sessions that "let the tool compute it" has not closed the defect it was aimed
at, and the reason is specific rather than general.

**The fields do their job perfectly.** Thirty ratios and forty-one denominators
were transcribed into replies without a single error. Compare Session 13's
certification, where the *same beats* produced a wrong ratio in both arms and a
wrong denominator. On the narrow thing each field states, the record is
unbroken: **a number in the payload is a number the model gets right.**

**The errors that remain are one step past what a field can state.** They are of
two kinds, and neither is a quantity any tool returns:

1. **Ordinal claims about a field** — "second-highest", "the lowest". The tool
   ships six values; the *order* of those six is still something the model works
   out, and it got it wrong twice in five runs while printing all six values
   correctly on the same screen.
2. **Set-intersection counts** — how many of an occupation's skills appear in a
   program's outcome tags. `skill_count` fixed the denominator because the
   denominator is a length. The numerator is a join across two servers, and no
   single tool result contains it.

Stated as the lesson it would become if this were written up: **putting a number
in the payload fixes the number, and moves the error to the next thing that is
not in the payload.** For a ranking, the payload would have to carry the rank —
a `rank` field, or the rows returned in ranked order with the ordering named in
the docstring. For an intersection tally, the payload would have to carry the
intersection, which means a tool that spans two servers and therefore a design
decision well outside this session's scope and probably outside the POC's.

I have deliberately not written any of this into `docs/LESSONS.md`, because item
5 is conditioned on success and this session did not succeed. It is here so the
finding is not lost.

---

## 8. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | `missing_per_student` on each rollup row, computed from the row's own fields; docstring extended; one test asserting the quotient on every row | **PASS.** §2 |
| 2 | `skill_count` on the occupation payload; docstring; one test asserting `len(skills)` on every occupation | **PASS.** §3 |
| 3a | Restart, then step 2 ×5: rankings consistent with `missing_per_student`, zero derived-figure errors | **FAIL — 3 of 5.** Two ordinal claims contradict the field. §4.2 |
| 3b | Step 7 ×5: every denominator matches `skill_count`, zero wrong tallies of any kind | **FAIL — denominators 5 of 5, tallies 2 of 5.** §5.2 |
| 4 | One full demo-verifier certification pass, zero incorrect figures, warts enumerated | **NOT RUN.** The fallback fired at item 3. §6 |
| 5 | LESSONS entries 4 and 9, `DEMO_VERIFICATION.md`, the commit | **NOT DONE.** Conditioned on success. §6 |
| — | FALLBACK: report and halt on a derived-figure error, no reversion, no re-run | **EXECUTED as written.** §6 |
| — | `pytest` green, 141+ | **PASS — 141 passed.** §9 |
| — | Diff confined to the permitted paths | **PASS.** Three files, all permitted; the forbidden paths are untouched. §1 |

---

## 9. Evidence — the suite and the pre-demo check

```
$ uv run pytest tests/ -q
141 passed in 49.69s
```

139 before this session, plus the two new tests. No test was removed, weakened,
or loosened to make anything pass.

**One flake, recorded because it is the known defect and not a new one.** The
first full-suite run after the two changes went 140 passed, 1 failed:
`test_skills.py::test_an_authorized_skill_is_accepted_and_named_on_the_receipt`.
pat asked the public-data question and the model replied *"The tool I would need
to list occupations is not available to me"* without calling it. The audit row
proves the tool was offered and the failure is the model's:

```
8155  orchestrator  answer_returned  pat
      {"tools_used": [], "tools_offered": ["get_occupation", "list_occupations"],
       "unoffered_calls": [], "servers": ["labor"], ...}
```

That is `docs/LESSONS.md` entry 4's "reply claims a tool is unavailable that the
caller holds", recorded since Session 7. It is not caused by the `skill_count`
change: `list_occupations` served kim successfully seconds earlier in the same
run (row 8147, `decision: ok`), and the test passed three times out of three on
re-run and again in the clean full-suite run above.

The pre-demo check, run **after** the suite as `CLAUDE.md` instructs:

```
$ docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
gateway-1  audit event 'auth_failed' dropped: POST http://audit:8030/events failed (ConnectError)
gateway-1  audit event 'auth_failed' dropped: POST http://audit:8030/events failed (ConnectError)
```

Both are the expected pattern, and the timestamps prove it — each drop lands
about a third of a second after the disruptive test stops the audit container on
purpose, one per suite run:

```
$ docker compose logs --since 45m --timestamps 2>&1 | grep -E "dropped|audit-1.*Shutting down"
gateway-1  2026-08-10T01:03:24.749Z  audit event 'auth_failed' dropped ...
gateway-1  2026-08-10T01:27:18.298Z  audit event 'auth_failed' dropped ...
gateway-1  2026-08-10T01:29:05.531Z  audit event 'auth_failed' dropped ...
audit-1    2026-08-10T01:03:24.442Z  INFO:     Shutting down
audit-1    2026-08-10T01:27:17.976Z  INFO:     Shutting down
audit-1    2026-08-10T01:29:05.213Z  INFO:     Shutting down
```

**Both measurement windows are after the last of those** — step 2 begins at
01:30:27Z and step 7 ends at 01:34:39Z — so no row either measurement depends on
was lost. Row counts confirm it: 40 rows in 8313–8352 for five step-2 runs, 69
rows in 8353–8421 for five step-7 runs, with five `router_classified`, five
`request_completed` and five `answer_returned` in each.

### Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-13.md && git commit          # bc5b715

# items 1 and 2 — both code changes before any measurement
docker compose restart mcp-canvas mcp-labor
uv run pytest tests/ -q                                               # 141 passed

# ground truth, recomputed from the databases
uv run python  # the two joins printed in §4 and §5

# item 3 — the measurements, toggle off, fresh conversation per run
uv run --with httpx python ask.py kim "Which occupations are growing fastest?" 1 warm-kim.json
uv run --with httpx python ask.py dana "How are my advisees doing?" 1 warm-dana.json
                                                                      # warm, rows 8303-8310
uv run --with httpx python ask.py kim "Which students seem to be struggling this term?" 5 step2.json
                                                                      # rows 8313-8352
uv run --with httpx python ask.py kim "Which fast-growing occupations would a Cybersecurity BS graduate qualify for?" 5 step7.json
                                                                      # rows 8353-8421

# acceptance
uv run pytest tests/ -q                                               # 141 passed
docker compose logs --since 30m 2>&1 | grep dropped                   # the disruptive test, above
```

The driver (`ask.py`) and the two run transcripts are in the session scratchpad
and are throwaway; nothing in the repository depends on them. `ask.py` posts to
the gateway with a real persona token, sends an empty `history` on every run so
each is a fresh conversation, and records the audit row range around the batch.

---

## 10. Open questions

1. **Do the two fields ship?** This is the one thing I stopped on. They are
   built, tested, additive, and demonstrably correct on everything they state —
   and the beats they were aimed at still state a wrong number, at a rate of
   2 of 5 and 3 of 5. Committing them is defensible (they strictly reduce the
   error surface and Session 13's exact Financial Analysts failure is gone).
   Discarding them is also defensible (they did not buy the acceptance they were
   built for). The brief did not anticipate the fields working and the beats
   failing anyway, so it gives no rule for this and I have not invented one.
   **They are uncommitted in the working tree; `git checkout` reverts them and
   `git commit` ships them.**

2. **The demo has never been certified with these fields in place.** Session
   13's certification is the current record in `DEMO_VERIFICATION.md`, and it was
   run against a stack without them. If the fields ship, the shipped
   configuration is uncertified; if they do not, the record is accurate as it
   stands. That is a fact about the deliverable, not a recommendation.

3. **Ranking is the next payload field, if there is another session.** §7 names
   it precisely: a `rank` on each rollup row, or rows returned in ranked order
   with the docstring saying so. It is the same technique one step further out
   and it is one short session's work. The intersection tally is not — that one
   needs a tool that spans two servers.

4. **Everything from Session 13 and earlier is committed.** The only commit this
   session is the archive move `bc5b715`. Nothing else has been committed and
   nothing has been reverted.
