# SESSION_REPORT — harness-poc Session 15

The session that closes the build. **No code was changed anywhere.** One
certification pass under a three-tier rubric declared in the brief, and the two
documents that carry the record forward.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

## The headline, in five sentences

**Eleven of twelve beats pass the strict tier; one fails, and it is demo moment
5.** Tier (a) — every figure a tool result or the database states — was not
violated anywhere in the pass. Across twelve replies, every headcount, total,
count, denominator, growth percentage, wage, GPA, login percentage, missing
count, seat count, term, grade, credit count, `skill_count`, `missing_per_student`
and intersection numerator was exact on recomputation from `data/*.db`. **That
has never happened before in a certification pass.**

**The one failure is behavioural, not arithmetic.** Noor's second turn — "And
how's BUS-201-A doing?" — was answered from the section list the model already
held, so `get_section_engagement` was never called, the spec-fixed refusal
sentence never appeared, and no amber row was written. The enforcement is
intact; the demonstration path did not exercise it. Per the brief's rule, this is
**reported, not accommodated**: it would need a code change and no change was
made.

**Both characterized residual classes came up clean on the beats Session 14
measured them on, and one of them turned up somewhere new.** Zero wrong ordinals
in step 2, zero wrong intersection numerators in step 7 — but three ordinal
errors elsewhere, two on the executive rollup beat. One run per beat is a single
draw, not a rate, and the report says so in those words.

**All standing checks are green, and I re-verified every one myself** rather than
taking the verifier's word: 25 model calls with cache telemetry and zero
zero-hit calls, all four spec-fixed refusal strings verbatim at the tool layer,
the faculty/dean asymmetry on an identical `args_hash`, zero dropped audit
events in the window, `tools_used ⊆ tools_offered` on all twelve
`answer_returned` rows, one guard fire and zero declines, and `active_skills`
correct on all twelve.

**The suite is green at 141 and the diff is two documents plus this file.**

---

## 1. What was done

| Brief item | Status |
|---|---|
| 1 — one full demo-verifier certification, steps 1–10 plus 2b plus the amber check, toggle off except 2b, standing checks in full, under the declared rubric, no re-runs | **DONE.** §3 |
| 2 — `docs/LESSONS.md` entries 4 and 9; the Session 14 §9 flake in the wart list; `DEMO_VERIFICATION.md` gains the Session 15 certificate and a presenter section | **DONE.** §5 |
| 3 — the commit | **DONE.** §8 |
| Rule — zero code changes anywhere | **HELD.** Proven in §7, not asserted |
| Rule — no re-runs | **HELD.** Every beat ran exactly once |

Session start: `SESSION_REPORT.md` (Session 14's) was moved to
`reports/session-14.md` and that move was committed by itself as **`2befec8`**,
per `CLAUDE.md`.

### One thing worth recording about how the session opened

This session was briefed twice. The first brief asked for per-intent reasoning
routing — a code change across `libs/harness_models/`, the gateway and the
orchestrator — and named "Session 15" as an existing baseline. Before writing
any code I checked and reported that no Session 15 existed: the repository goes
Session 13 (certified, the standing record) → Session 14 (fields built,
measurement halted on its fallback, no certification), and no branch, stash,
reflog entry or file in the tree contained the string. The brief was then
withdrawn and replaced with the one this report answers.

**No work product from the first brief exists.** No file was created or edited
under it; the only action taken was the archive move above, which `CLAUDE.md`
requires at every session start regardless. The reasoning-routing experiment was
never built and was never measured, and nothing in this report or in the two
documents describes it.

---

## 2. The rubric, and how it was applied

Declared in the brief and quoted verbatim in the verifier's instructions and in
`DEMO_VERIFICATION.md`:

> (a) Any stated figure that a tool result or database states — values, totals,
>     counts, denominators, growth, wages, GPAs, percentages — is scored strictly;
>     one error fails the beat.
> (b) The two characterized residual classes — ordinal claims about tool-stated
>     values, and cross-server intersection numerators — do not fail a beat when
>     the underlying values beside them are exact; each instance is recorded in a
>     RESIDUALS section with its row reference, beside Session 14's measured rates
>     (ordinals wrong in 2 of 5 step-2 runs; intersection tallies wrong in 3 of 5
>     step-7 runs).
> (c) Presentation findings (preambles, verbosity) are recorded as warts.

I tightened two definitions before the pass so tier (b) could not be used as an
escape hatch, and both tightenings cut against the pass rather than for it:

- An ordinal claim qualifies for (b) **only if** the values it is about are
  printed correctly in the same reply. A wrong value is (a) and fails the beat.
- The **denominator** in "n of N" is `skill_count`, which a tool states, so a
  wrong denominator is (a). Only the numerator is (b). Growth percentages,
  wages and skill list contents are all (a).

---

## 3. The certification — rows 8552–8659

One pass by the demo-verifier agent, 108 rows, 2026-08-10 02:09:29–02:18:16Z.
Driven through the gateway's `/chat` with real RS256 persona tokens; step 4 ran
`./scripts/demo_bypass.sh` unmodified; step 5b carried step 5a's rendered prose
back as client-held history; step 10 was raw curl at six ports. A warm-up as kim
with a question outside the demo script occupies rows 8552–8556 and is excluded
from scoring. Every figure was recomputed from `data/*.db` read-only, and
nothing had drifted from the values pinned in earlier sessions.

### 3.1 Result — 11 of 12 on tier (a)

| Beat | Verdict |
|---|---|
| 1 | PASS — 25 / 9 / 8 / 6 exact; all eleven named students verified |
| 2 | PASS — all six programs' cells exact, **including all six `missing_per_student` values**, and every ordinal correct |
| 2b | PASS — row 8577 carries `["plain_language"]`; all figures exact |
| 3 | PASS — gate refusal with **zero tool rows**; all 24 occupation figures exact |
| 4 | PASS — `tools that actually ran: none`; mcp-colleague refusal verbatim, row 8586 amber |
| **5** | **FAIL** — 5a and 5c pass; **5b's tool call never happened** |
| 6 | PASS — every seat count, prereq, term and grade exact; CS-460 correctly blocked |
| 7 | PASS — all four `skill_count` denominators **and all four intersection numerators** exact |
| 8 | PASS — six distinct `get_course_outcomes` calls before any catalog-wide claim; all 78 skill strings exact |
| 9 | PASS — viewer serves; every beat on the record |
| 10 | PASS — 401 at all six token-validating services, twelve probes, twelve `auth_failed` rows |
| amber check | PASS — row 8655 carries `"reason": "unknown"` **and** `"decision": "refused"` |

### 3.2 The failure, stated fully

**Beat 5b — noor, "And how's BUS-201-A doing?" — rows 8594–8598.** The reply is
honest and its stated section ids are correct:

> I don't have BUS-201-A in my sections this term. My roster shows only
> CYB-210-A and CYB-310-A [canvas]. I can't report on a section I don't teach.

The tool layer was never reached. I verified this directly rather than accepting
it — the whole beat contains one tool call:

```
8594 gateway       router_classified noor {"intent": "program_aggregate", ...}
8595 mcp-canvas    tool_call         noor {"tool": "get_my_sections", "args_hash": "44136fa355b3", "decision": "ok"}
8596 gateway       request_completed noor {"tools_used": ["get_my_sections"], "latency_ms": 5203.9}
8597 orchestrator  answer_returned   noor {"tools_used": ["get_my_sections"],
                     "tools_offered": ["get_course_outcomes", "get_my_sections", "get_occupation",
                                       "get_program_curriculum", "get_section_engagement",
                                       "list_occupations"], "unoffered_calls": [], ...}
8598 orchestrator  tool_call         noor {"tool": "get_my_sections", "via": "orchestrator"}
```

Row 8597 shows `get_section_engagement` **was** offered. The model held the tool
and did not call it. Demo moment 5's claim is not "the model declines politely";
it is that the tool server refuses by name and the refusal lands amber on the
audit page. That did not happen, so the beat fails.

**This is a known instability, not a new regression.** Session 6 recorded exactly
this outcome at rows 3616–3623, in the same shape and for the same reason.
Session 11 measured the same loss in roughly half of ten runs with extended
reasoning enabled. Session 12 measured it in 2 of 5 runs with the plain-language
skill active against 0 of 4 with it off. Sessions 7 through 13 drew a call; this
pass, in the shipping configuration with no skill active, drew a miss. The
structural cause is that `get_my_sections` returns the section list, which makes
"is BUS-201-A mine?" answerable without calling the tool that refuses.

**It was not fixed and no re-run was attempted.** The brief's rule is explicit —
*a certification that requires a code change to pass is reported, not
accommodated* — and re-running until the beat agrees would make the whole
exercise worthless.

The enforcement itself is fine, proven in the same pass by direct probe:

```
8656 mcp-canvas tool_call noor {"tool": "get_section_engagement", "args_hash": "8dcd893de78e",
       "decision": "refused",
       "reason": "Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean."}
8657 mcp-canvas tool_call kim  {"tool": "get_section_engagement", "args_hash": "8dcd893de78e", "decision": "ok"}
```

### 3.3 Residuals — tier (b), four instances

Full text and row references are in `DEMO_VERIFICATION.md`. In summary: two
ordinal errors on beat 5c (row 8605 — BUS-BS called "the lowest" when IS-MS is
lower, and IS-MS called "best on both measures" when its login rate is fourth of
six), one comparative-to-a-mean error on beat 2b (row 8577 — HIM-BS called above
average on a quiet rate where it is 10.4% against a 10.63% mean), and one
borderline case on beat 7 (row 8621 — "no other … reaches even half coverage"
where one occupation is exactly half). In all four, the values the claim is
about are printed correctly in the same reply.

| Class | Session 14 | This pass |
|---|---|---|
| Ordinal claims, step 2 | wrong in **2 of 5** runs | **0 of 1 wrong** |
| Intersection numerators, step 7 | wrong in **3 of 5** runs | **0 of 1 wrong** |
| Ordinal claims, anywhere | not measured outside step 2 | **3 instances**, beats 5c and 2b |

**This is one run per beat — a single draw, not a rate.** Drawing zero errors
from a 2-in-5 process happens about 60% of the time and from a 3-in-5 process
about 40% of the time, so the pass is fully consistent with both rates being
unchanged. The report says this plainly and does not claim an improvement.

The finding that is genuinely new: **the ordinal class is not confined to step
2.** Session 14's `missing_per_student` removed the need to derive a ratio, and
no derived ratio was wrong anywhere in this pass — but the model still misread
the ranking of ratios it had itself printed correctly, on the executive rollup
beat rather than on the one the field was aimed at.

### 3.4 Warts — tier (c), eight from the pass plus one carried forward

The two that matter for a projector: **beat 8 leaked its reasoning into the
user-visible reply** (row 8640 — *"deep learning — wait, that's not in any
program. Let me be systematic."*) on the beat where the room is told it is
watching program strategy; and **beat 7 opened with a preamble promising an
order it then broke** (row 8621). The rest are a citation-format defect on beat
2, a "DATA-MS" typo on 2b, an editorial imprecision on 3b, 5c re-rounding the
shipped three-decimal ratios to two, and beat 6 skipping
`get_student_degree_progress` so "9 of 24 credits" never appears.

**One of the eight is a latent code defect and I want it read as such.**
`get_enrollment_trends` orders terms alphabetically rather than chronologically
(`services/mcp-colleague/app.py:418-421`, `ORDER BY program_code, term`): the
strings sort 2025FA, 2025SP, 2026FA, 2026SP where the true order is 2025SP,
2025FA, 2026SP, 2026FA. Beat 2 read the rows as a time series and concluded no
programme is shrinking. That holds first-to-last on the true chronology, but
CS-BS does fall 50 to 47 in the most recent term. No stated figure is wrong, so
it fails nothing under the rubric — **and it would need a code change, so none
was made.**

The carried-forward wart is Session 14 §9's flake, now written into the record
with its rate: a reply claiming an offered tool is unavailable, roughly one suite
run in four or five, `docs/LESSONS.md` entry 4's known class. **It did not appear
anywhere in this pass.**

### 3.5 Standing checks — all green, and independently re-verified

The verifier reported these; I re-computed every one myself from the audit
service before writing them down.

```
$ curl -s "localhost:8030/events?limit=300" | python3 <window analysis>
window rows: 108 range 8552 - 8659
answer_returned: 12  router_classified: 13
model calls with telemetry: 25  min hits: 896  zero-hit calls: 0
rows violating tools_used subset tools_offered: none
rows missing unoffered_calls: none
active_skills non-empty: [(8577, ['plain_language'])]
declines (ungrounded true): none
regenerated: [8605]
ungrounded fires: [8601]
Counter({'tool_call': 56, 'router_classified': 13, 'request_completed': 12,
         'auth_failed': 12, 'answer_returned': 12, 'skill_refused': 1,
         'answer_ungrounded': 1, 'refused_at_gate': 1})
```

| Check | Result |
|---|---|
| Prompt cache | 25 calls with telemetry, minimum `prompt_cache_hit_tokens` **896**, **zero** zero-hit calls |
| Four spec-fixed refusal strings, verbatim at the tool layer | **All four** — row 8586 in-beat, rows 8656/8658/8659 by probe |
| Faculty/dean asymmetry | Identical `args_hash 8dcd893de78e`: row 8656 noor refused, row 8657 kim served |
| Dropped audit events in the window | **Zero** |
| `tools_used ⊆ tools_offered` | **12 of 12**; `unoffered_calls` present and empty on all twelve |
| Guard ledger | **1 fire, 1 regeneration, 0 declines** (row 8601) |
| `active_skills` discipline | Row 8577 `["plain_language"]`; the other eleven `[]` |

**One thing to be precise about: three of the four spec-fixed refusal strings
came from direct probes after the beats, not from the beats themselves.** Only
`get_my_advisees requires the advisor role.` was produced in-beat, by the bypass.
That is normal — Session 13 did the same for the strings the script cannot reach
— but the BUS-201-A string is a different case this time: it is normally
produced by beat 5b, and this pass had to probe for it because beat 5b never
dialled the server. The string exists and the enforcement works; the
demonstration did not show it.

---

## 4. Deviations

**One, and it is a classification judgement rather than a departure from the
brief.** Residual 3 — beat 2b's "HIM-BS has both a higher-than-average quiet rate
and a higher-than-average missing-work rate" — is a claim about position relative
to a mean, not literally a rank or a superlative, so it sits adjacent to tier
(b)'s definition rather than squarely inside it. I recorded it under (b) because
it states no figure of its own and the figure it is about is printed correctly one
paragraph above, and I flagged the judgement in both the certificate and here so
it can be ruled otherwise. Under the alternative reading it is a wart, not a
residual; under no reading is it tier (a), so **the verdict does not move either
way.**

A second, smaller judgement, flagged the same way: beat 2b's "DATA-MS" for DAT-MS
is a programme code rather than a figure, so I recorded it as a wart. If a code
counts as a database-stated value, beat 2b becomes a tier (a) failure and the
score becomes 10 of 12. I do not think it does — the rubric enumerates figures —
but the reader should know the score has that hinge in it.

Nothing else deviates. No beat was re-run, no fix was made after measurement
began, and no code was touched at any point.

---

## 5. The documents

**`DEMO_VERIFICATION.md`** gains a Session 15 section as the current record, and
Session 13's is demoted to superseded. The section carries the window, the rubric
quoted verbatim, the three-tier verdict, the per-beat table with beat 5 broken
out, the RESIDUALS section with the rate comparison, the WARTS section, the
standing checks, the row map, and a seed assessment.

It also gains **RESIDUAL RISKS AND PATTER**, written for a presenter:

- **Step 2** — the burden leader is reliable (6 of 6 across Sessions 14 and 15);
  avoid inviting full rankings or "which is lowest"; if the reply volunteers an
  ordinal, the table beside it is exact. The honest line is that the values come
  from tools and the prose comparisons are the model — which is the production
  argument for routing reasoning budget by intent rather than paying for it
  everywhere.
- **Step 7** — denominators, growth, wages and the headline 8-of-8 are reliable;
  intersection tallies can contradict their own lists, and if they do, the lists
  are the truth. The honest line is that the join is performed live by the model,
  visibly and checkably, and the audit page holds the tool results to check it
  against.
- **Demo moment 5** — new, and the presenter must know it: check the audit page
  for an amber `get_section_engagement` row before promising one, and fall back
  on moment 4's bypass row, which is deterministic because a script makes the
  call rather than a model.
- **Demo moment 4** — deterministic, the strongest beat in the script, and the
  one to fall back on when any model-driven beat wobbles.
- **The plain-language beat** — carried forward from Session 13 unchanged.

**`docs/LESSONS.md` entry 4** gains applications seven and eight in its table —
Session 14's `missing_per_student` and `skill_count` — and the score is now
**eight for eight on what the payload states**. It then records the boundary,
with Session 14 §7's sentence near-verbatim: *putting a number in the payload
fixes the number, and moves the error to the next thing that is not in the
payload.* Both residual classes are named, and both reasons for not chasing them
are written down: a rank could be a field and was declined deliberately, because
chasing each newly-exposed derived quantity is an unbounded regress and the
residual is now characterized rather than unknown; the intersection is different
in kind, because **a cross-server tally tool would replace the synthesis demo
moments 7 and 8 exist to demonstrate with a lookup.** That is the one place in
the record where "put the number in the payload" is the wrong answer.

**Entry 9** gains the final scoreboard for the arithmetic defect class: what
payload fields closed (eight fields, every one held, and Session 15's pass with
no tool-stated figure wrong anywhere), what reasoning mode closed in the Session
10 A/B (the table, unchanged) and what it cost in Session 11 (the refusal, about
half of ten runs), and what remains in the shipping configuration with the
measured rates for both residual classes.

---

## 6. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | One full demo-verifier pass — steps 1–10 plus 2b plus the amber check, toggle off except 2b, standing checks in full, under the declared rubric | **DONE.** 12 items scored. §3 |
| — | The certificate states all three tiers explicitly in its verdict | **DONE.** "Eleven of twelve beats pass tier (a). One beat fails. Four tier-(b) residual instances … Eight tier-(c) warts … plus one standing wart carried forward." |
| — | Residuals recorded with row references, beside Session 14's rates | **DONE.** Four instances, each with its row; the rate table is in §3.3 and in the certificate |
| — | No re-runs of any beat for any reason | **HELD.** Every beat ran exactly once |
| 2 | LESSONS entry 4 — applications seven and eight, scored honestly, with the boundary | **DONE.** §5 |
| 2 | LESSONS entry 9 — the final scoreboard | **DONE.** §5 |
| 2 | Session 14 §9's flake in the wart list | **DONE.** Wart 9, with its rate and its row evidence |
| 2 | DEMO_VERIFICATION — Session 15 certificate as current record, superseding Session 13 | **DONE.** §5 |
| 2 | RESIDUAL RISKS AND PATTER, with moment 5 and bypass patter included | **DONE**, with one addition the brief could not have anticipated: moment 5's patter now carries the measured risk that its refusal may not fire. §5 |
| 3 | The commit | **DONE.** §8 |
| — | Zero code changes anywhere | **HELD.** Proven in §7 |
| — | A certification requiring a code change to pass is reported, not accommodated | **HELD.** Beat 5b and the `get_enrollment_trends` ordering are both reported and both unfixed |
| — | `pytest` green (141) | **PASS — 141 passed.** §7 |
| — | Diff confined to `docs/LESSONS.md`, `DEMO_VERIFICATION.md`, `SESSION_REPORT.md` | **PASS.** §7 |
| — | Certification with no failures | **NOT MET — 11 of 12.** Beat 5b failed and was not fixed. §3.2 |

---

## 7. Evidence

### The suite, run before the certification

```
$ uv run pytest tests/ -q
141 passed in 50.39s
```

No test was added, removed, weakened or loosened — no test file was touched at
all.

### The diff

```
$ git diff --stat
 DEMO_VERIFICATION.md | 367 ++++++++++++++++++++++++++++++++++++++++++++++++++-
 docs/LESSONS.md      | 117 ++++++++++++++--
 2 files changed, 475 insertions(+), 9 deletions(-)
```

Plus this file. **Zero code changes, proven rather than asserted:**

```
$ git diff --exit-code --stat services/ libs/ tests/ config/ apps/ scripts/
UNCHANGED: services, libs, tests, config, apps, scripts
```

`git status --porcelain` was empty immediately before the certification pass and
immediately after it, and no container was restarted at any point in the session.

### The pre-demo check, run after the suite as `CLAUDE.md` instructs

```
$ docker compose logs --since 30m 2>&1 | grep "dropped"
gateway-1  audit event 'auth_failed' dropped: POST http://audit:8030/events failed (ConnectError)

$ docker compose logs --since 45m --timestamps 2>&1 | grep -E "dropped|Shutting down"
gateway-1  2026-08-10T02:06:08.665Z  audit event 'auth_failed' dropped ...
audit-1    2026-08-10T02:06:08.340Z  INFO:     Shutting down
```

One drop, and it is the expected pattern: it lands 0.325 seconds after the test
suite's disruptive test stops the audit container on purpose. **The certification
window opened at 02:09:29Z, three minutes and twenty-one seconds later**, so no
row the certification depends on was lost. The verifier confirmed zero drops
inside its own window independently, with a `--since` scoped to it.

### Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-14.md && git commit          # 2befec8

# acceptance, before the pass
uv run pytest tests/ -q                                               # 141 passed
curl -s "localhost:8030/events?limit=1"                               # watermark: row 8551

# the certification — the demo-verifier agent, one pass, no re-runs
# steps 1-10 + 2b + the appended amber check                          # rows 8552-8659

# independent re-verification of every standing check and the 5b failure
curl -s "localhost:8030/events?limit=300" | python3 <window analysis>

# acceptance, after
git diff --exit-code --stat services/ libs/ tests/ config/ apps/ scripts/
docker compose logs --since 30m 2>&1 | grep dropped                   # the disruptive test, above
```

The verifier's artefacts — one request/reply/raw triple per beat, the 108-row
audit window dump, its independent ground-truth recomputation, the 401 matrix,
the viewer copy and its driver scripts — are in the session scratchpad under
`cert15/`. They are throwaway; nothing in the repository depends on them.

---

## 8. The commit

One commit, following this report:
`session 15: characterization certification; lessons and demo record closed`.

Two files plus this one. It is the final commit of the build.

---

## 9. Open questions

1. **Demo moment 5 is not deterministic, and that is now measured rather than
   suspected.** The beat has been lost before — Session 6 in the same shape,
   Session 11 in about half of ten runs under reasoning, Session 12 in 2 of 5
   runs with the skill on — and this pass lost it in the shipping configuration
   with nothing switched on. Nobody has ever measured its rate in the plain
   configuration. If one more session existed, five runs of moment 5 would be the
   most valuable five runs left in the project: the demonstration's second-best
   beat currently rests on an unmeasured coin flip, and the presenter section now
   tells the presenter to check the audit page before promising the refusal.

   The fix, if one is wanted, is not a prompt. `docs/LESSONS.md` entry 12 already
   says the receipt should never depend on the model volunteering to hit the
   boundary, and `docs/patches/README.md` names the shape of the answer — re-drive
   the turn with the tool-first instruction rather than letting a first answer
   drawn from held context stand. That variant has never been built or measured.

2. **`get_enrollment_trends` sorts terms alphabetically** (§3.4). It is a
   one-line ordering fix in `services/mcp-colleague/app.py` and it was not made,
   because this session permitted no code changes. The model read the rows as a
   time series in this very pass. It is the last known code defect in the build.

3. **The ordinal residual is not where anyone expected it.** It has been treated
   as a step-2 problem since Session 13, and Session 14's field removed the
   derived ratio that seemed to cause it — yet this pass produced zero ordinal
   errors on step 2 and three elsewhere, two of them on the executive rollup. If
   the class is ever chased, it should be chased across every beat that prints
   more than one comparable value, not on the beat where it was first noticed.

4. **Everything is committed.** The only commits this session are the archive
   move `2befec8` and the one that follows this report.
