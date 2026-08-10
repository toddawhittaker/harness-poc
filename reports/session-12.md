# SESSION_REPORT — harness-poc Session 12

The last session of the build. Three pieces of work: a micro-fix with a proven
pattern, an additive feature behind a kill switch, and the housekeeping that
makes the repository readable by someone who was never in the room.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

## The headline, in four sentences

**Both items were built, both work, and the freeze certification is not clean.**
The membership fix closed the defect it was aimed at — 5 of 5 measured runs put
every student in the right group, and the certification pass confirmed it on the
exact two students Session 11 got wrong. The skills toggle is governed, kill-
switched, and costs nothing when the switch is off: two arms measured
indistinguishable from the certified configuration, and the certification pass
gave step 2b a clean bill with `active_skills` on the right row and only the
right row.

**The pass failed one beat, and it is not this session's work.** Step 5c stated
"78 missing submissions" where the databases say 112 — the model added the first
four rows of its own table and stopped. That is the wrong-secondary-number class
Session 11 recorded three times, it ran with the skills toggle off, and neither
thing built this session touches mcp-canvas. **The pre-authorized fallback was
therefore not executed**: it is scoped to a failure the skills feature causes,
and turning skills off would not change this figure by one digit. §6.3 sets out
that reasoning in full, and §6.4 gives the fix, which this session was not
permitted to make.

**One further finding, larger than the failure: switching the skill on degrades
demo moment 5** (§5.4). The toggle ships off by default and
`DEMO_VERIFICATION.md` now says never to use it on that beat.

---

## 1. The diff

Session start: `SESSION_REPORT.md` was moved to `reports/session-11.md` and that
move was committed by itself as **`d77a2f5`**, per `CLAUDE.md`.

```
 .env.example                    |  10 ++
 apps/ui-advisor/app.py          |  14 +-
 apps/ui-advisor/harness_chat.py |  59 +++++++++--
 apps/ui-exec/app.py             |  14 +-
 apps/ui-exec/harness_chat.py    |  59 +++++++++--
 docker-compose.yml              |  12 ++
 docs/LESSONS.md                 | 114 ++++++++++++++++++++--
 docs/patches/README.md          |  33 +++++--
 scripts/seed.py                 |  18 ++++
 services/gateway/app.py         |   8 +-
 services/mcp-colleague/app.py   |  37 +++++--
 services/orchestrator/app.py    |  50 +++++++++-
 tests/test_tool_results.py      |  46 ++++++++
 config/skills.yaml              | new
 services/orchestrator/skills.py | new
 tests/test_skills.py            | new
```

Plus `DEMO_VERIFICATION.md` and this file, and the regenerated `data/*.db`
(gitignored). **One path is outside the brief's permitted list —
`services/gateway/app.py` — and §8 deviation 1 explains why it had to be.**
Nothing in `services/audit/`, `services/mcp-canvas/`, `services/mcp-kuali/`,
`services/mcp-labor/`, `services/orchestrator/prompts.py` or
`services/orchestrator/grounding.py` was touched:

```
$ git diff --exit-code services/audit/ services/mcp-canvas/ services/mcp-kuali/ \
                       services/mcp-labor/ services/orchestrator/prompts.py \
                       services/orchestrator/grounding.py
(clean)
```

---

## 2. Housekeeping

### 2.1 The patches were where they should be

```
$ ls docs/patches/
README.md  item2-marker-correction.patch  session-11-full.patch
```

Both patches the brief named are present, tracked, and were copied in by the
user as intended. `docs/patches/README.md` already existed — Session 11 wrote
it — and already covered what each patch is, the commit it applies to, and why
the work was reverted. Three things were added rather than re-written:

- that the five tests **pass**, taking the suite from 133 to 138 when the patch
  is applied to `0e08b1c`;
- **the recommended MVP variant**, stated as a recommendation and explicitly
  labelled unmeasured: take the marker correction *and* keep the tool-first
  retry, so the correction no longer consumes the rejection that drove the tool
  call. Neither Session 11 nor Session 12 measured it;
- three stale references to `SESSION_REPORT.md` repointed at
  `reports/session-11.md`, which is where that report now lives.

### 2.2 LESSONS entry 12 already existed

The brief asked for a new entry 12 — an enforcement receipt must never depend on
the model volunteering to hit the boundary, and when proof of refusal matters it
should be generated deterministically, the bypass script being the pattern.
**Session 11 had already written exactly that entry**, including the bypass
script as the named pattern. It was left in place; only its stale
`SESSION_REPORT.md` reference was repointed. Writing a second copy would have
been the worse outcome.

### 2.3 LESSONS entry 13 is new

Skills as governed behavioural configuration, and the activation taxonomy. §7.2.

---

## 3. Item 1 — the membership lists

Session 11 §9.3, proposed by the verifier and left unbuilt.

### 3.1 What was built

`services/mcp-colleague/app.py` only. `AdviseeRoster` gains three fields:

```python
    advisee_count: int
    flagged_count: int
    quiet_count: int
    flagged_and_quiet_count: int
    flagged_ids: list[str]
    quiet_ids: list[str]
    flagged_and_quiet_ids: list[str]
    advisees: list[Advisee]
```

and the tool computes each group once and derives the count from it, so a count
and its list cannot disagree — the count is no longer computed separately:

```python
        flagged = [a for a in advisees if a.term_grade_flags]
        quiet = [a for a in advisees if a.last_login_days > QUIET_AFTER_DAYS]
        both = [a for a in flagged if a.last_login_days > QUIET_AFTER_DAYS]
```

The tool docstring gains one sentence saying the lists are authoritative: *"an
advisee is in a group if and only if this result puts their id in that group's
list, and every count is the length of the list beside it."* No prompt file was
touched.

### 3.2 The test

`tests/test_tool_results.py::test_the_advisee_roster_names_who_is_in_each_group`.
One test, both halves: each list's length equals its count, and each list holds
exactly the advisees the predicate selects from the rows shipped beside it.

### 3.3 The seed

`scripts/seed.py::verify` gains one assertion and one printed line:

```
    membership lists ship with the counts: flagged 9, quiet 8, both 6
      (S-1031, S-1035, S-1038, S-1043, S-1047, S-1054)
```

The assertion pins all four sizes at 25/9/8/6 **and** requires
`flagged ∩ quiet == flagged_and_quiet`, so the three lists cannot drift from the
counts above them in either direction. Green on the first run, nothing retuned;
every other invariant in `verify()` held unchanged.

```
$ uv run scripts/seed.py
verified:
  dana advises 25, of whom 9 carry a term grade flag and 8 have not logged in for >10 days
    both flagged and quiet: 6
    quiet with no flag raised: 2 (S-1049, S-1052)
    flagged while still logging in: 3 (S-1045, S-1048, S-1051)
    membership lists ship with the counts: flagged 9, quiet 8, both 6 (S-1031, S-1035, S-1038, S-1043, S-1047, S-1054)
  ...
$ docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
```

### 3.4 The measurement — step 1 ×5, rows 6708–6730

Five fresh conversations as dana through the gateway, ground truth 25 advisees /
9 flagged / 8 quiet / 6 both, with `flagged_and_quiet` = S-1031, S-1035, S-1038,
S-1043, S-1047, S-1054; `flagged-and-active` = S-1045, S-1048, S-1051;
`quiet-and-unflagged` = S-1049, S-1052.

| Measure | Target | Result |
|---|---|---|
| Every student in the right group | 5 of 5 | **5 of 5** ✔ |
| Self-contradiction on screen | 0 | **0** ✔ |
| Counts stated verbatim, never recomputed or overruled | 5 of 5 | **5 of 5** ✔ |
| Stated all four counts | — | 1 of 5 (run 1) |
| Stated 25, 9 and 6, leaving 8 implicit | — | 4 of 5 |
| Guard fires / declines | 0 | **0 / 0** ✔ |
| Model calls with zero cache hits | 0 | **0** ✔ |

The three group headings were exact in every run, in all three directions:
S-1045 (last login today) never appeared under "flagged and quiet", and S-1054
(25 days) never appeared under "flagged but still logging in". **That is the
Session 11 defect, closed.** Run 1's opening sentence:

> You have 25 advisees total. Of those, 9 have grade flags this term, 8 have
> gone quiet (no login in over 10 days), and 6 are both flagged and quiet — the
> most at-risk group.

The residual is unchanged and no tool field can fix it: in four of five runs the
model says "9 of your 25 … 6 of those are also quiet" and leaves the reader to
add the two unflagged. That is not a wrong statement. It is Session 10 §8.4,
recorded again.

Median latency 8.7s; every run cited `[colleague]`; no invented ids.

---

## 4. Item 2 — the skills toggle

### 4.1 What was built

**`config/skills.yaml`** — one skill, `plain_language`, roles
`[advisor, dean, faculty, adjunct]`, `activation: user`. Its instructions ask for
short declarative sentences, everyday words, no filler opener, and an inline
gloss for any term with no everyday equivalent — followed by an explicit
carve-out: *"This shapes wording only. Every figure, name, id, code, term and
percentage stays exactly as the tool returned it. Every citation marker stays
where it was. A refusal is relayed with the specifics it gave you… do not
soften, shorten or omit a refusal."*

**`services/orchestrator/skills.py`** — the registry loader and the boundary.
`resolve(names, roles)` raises `SkillRefused` on the first name that is unknown
or that the caller's roles do not cover; `skill_message(skills)` builds the one
trailing message. `SKILLS_ENABLED` is read from the environment at import.

**`services/orchestrator/app.py`** — `/chat` accepts `active_skills: [names]`.
Validation happens before anything expensive; a refusal returns a courteous
sentence, writes a `skill_refused` audit row with the machine-readable reason,
and stops the request. The instructions are injected by
`message_history(history, skill_prompt)`, which appends **one** `ModelRequest`
after the history and before the question — never inside `SYSTEM_PROMPT`, which
is byte-identical to Session 11's. `answer_returned` gains `active_skills`, and
gains it only while the feature is on.

**`services/gateway/app.py`** — `active_skills` added to the request model and
forwarded verbatim. No validation there; see §8 deviation 1.

**`apps/ui-advisor` and `apps/ui-exec`** — a Chainlit `Switch` labelled "Plain
language", default off, shown only when `SKILLS_ENABLED`. `on_settings_update`
stores the name in the session; `answer()` sends it. The receipts line under the
reply reads `` `plain language · tools: …` `` when the skill is on and is
unchanged when it is not. `harness_chat.py` stays byte-identical across the two
apps, which `tests/test_ui_apps.py` enforces:

```
$ md5sum apps/*/harness_chat.py
af2aed6942f1fd0b99bf895e53432737  apps/ui-advisor/harness_chat.py
af2aed6942f1fd0b99bf895e53432737  apps/ui-exec/harness_chat.py
```

**`docker-compose.yml` and `.env.example`** — `SKILLS_ENABLED`, default true, set
on the orchestrator and on both surfaces so one setting darkens the feature end
to end. `SKILLS_PATH: /config/skills.yaml` on the orchestrator; `config/` was
already mounted read-only there.

**The surface path was proven end to end, not assumed.** A scripted socket.io
client signed into ui-advisor as kim over a real `POST /login`, emitted
`chat_settings_change {"plain_language": true}`, then sent a question. Two runs,
and both produced an `answer_returned` row carrying the skill:

```
7260  2026-08-10T00:16:55Z  kim  active_skills=['plain_language']  tools=['list_occupations']
7255  2026-08-10T00:16:18Z  kim  active_skills=['plain_language']  tools=['list_occupations']
```

So the whole chain is exercised: Chainlit switch → `on_settings_update` →
`cl.user_session` → `answer()` → gateway → orchestrator → audit. The two rows
landed inside the certification window and the verifier was told to exclude
them; they are the only rows in that window carrying `active_skills` that do not
belong to the pass, apart from step 2b's.

### 4.2 The tests — `tests/test_skills.py`, three of them

Live stack, real tokens, same as everything else in the suite.

- **unknown skill refused** — dana asks with `["definitely_not_a_skill"]`: the
  reply names the skill, `tools_used` is empty, and a `skill_refused` row carries
  `reason: "unknown"`.
- **unauthorized skill refused** — a token minted with identity-stub's own key
  carrying `roles: ["registrar"]`, valid in every other respect, asks for
  `plain_language`: refused, `reason: "not_authorized"`. **Nothing is weakened**;
  the token passes signature, issuer, audience and expiry, and is refused on the
  one thing under test. This is how the boundary is reachable at all — the
  registry grants `plain_language` to all four data roles, so no persona is
  unauthorized for it (§8 deviation 2).
- **authorized skill accepted, and on the receipt** — pat, through the gateway,
  gets an answer, a real tool call, and an `answer_returned` row carrying
  `active_skills: ["plain_language"]`.

All three skip rather than fail when `SKILLS_ENABLED` is off, probing the running
container rather than reading the environment: a suite that went red for a
working kill switch would be pressure to leave the switch on.

---

## 5. The measurements

Every arm was warmed with four personas before any timed run. All figures were
recomputed from `data/*.db` rather than quoted.

| Window | Rows | What |
|---|---|---|
| A | 6708–6730 | step 1 ×5, the membership fix (§3.4) |
| B | 6904–6941 | **arm 1**, `SKILLS_ENABLED=false`: step 1 ×2, moment 5 ×2, bypass ×1 |
| C | 6966–7004 | **arm 2**, `SKILLS_ENABLED=true`, toggle off: the same three |
| D | 7005–7041 | kim, toggle **off**: step 2 ×3, step 3b ×2 (the "before") |
| E | 7042–7077 | kim, toggle **on**: step 2 ×3, step 3b ×2 |
| F | 7078–7152 | noor, toggle **on**: demo moment 5 ×5 — the finding |
| G | 7153–7250 | **the freeze certification** — the demo-verifier pass, §6 |
| — | 7251–7260 | the ui-advisor socket.io probes (§4.1), excluded from G by the verifier |

### 5.1 Arm 1 — the kill switch, exercised

`.env` set to `SKILLS_ENABLED=false`, `docker compose up -d` recreating the
orchestrator and both surfaces. Verified on the live containers before any run:

```
/harness-poc-orchestrator-1 SKILLS_ENABLED=false
/harness-poc-ui-advisor-1   SKILLS_ENABLED=false
```

| Check | Result |
|---|---|
| Step 1 ×2 | Both clean; every student in the right group |
| Demo moment 5 ×2 | **2 of 2** ended in the relayed mcp-canvas refusal, amber rows **6924** and **6936** |
| Bypass ×1 | `tools_used: []`, mcp-colleague refusal row **6941** carrying `get_my_advisees requires the advisor role.` verbatim |
| `active_skills` anywhere in the window | **absent from all 38 rows** |
| Model calls with zero cache hits | 0 (minimum hit tokens 896) |
| Guard | one fire, one regeneration, zero declines — the five-session-old `[colleague]`-for-canvas misfire, recovered |

The 38-row window was searched for the string "skill" in any field of any row:
**none**.

### 5.2 Arm 2 — the feature on, the toggle off

`SKILLS_ENABLED=true` on all three containers, nothing switched on.

| Check | Result |
|---|---|
| Step 1 ×2 | Both clean |
| Demo moment 5 ×2 | **2 of 2** refusals, amber rows **6986** and **6999** |
| Bypass ×1 | clean; mcp-colleague refusal row **7004** |
| `active_skills` on `answer_returned` | `[]` on every row — present, and empty |
| Model calls with zero cache hits | 0 (minimum 896) |

The one observable difference between arms 1 and 2 is the empty `active_skills`
field. Behaviour was indistinguishable: same refusals, same rows, same counts.
**The toggle's existence costs nothing.**

### 5.3 The toggle on — register, figures, citations

Kim, the same two questions, five runs each side.

| Measure | Toggle off | Toggle on |
|---|---|---|
| **Step 2** — words per reply (median) | 277 | **213** |
| Sentence length, median words | 15.0 | 16.0 |
| Institutional-vocabulary hits ("disengaged", "cohort", "at-risk", …) | 5 | **2** |
| Plain paraphrases ("have not logged in", "stopped showing up", …) | 12 | **19** |
| Replies opening with visible deliberation | **3 of 3** | **0 of 3** |
| Median latency | 12.9s | **9.2s** |
| Every figure exact against the databases | 3 of 3 | **3 of 3** |
| Any individual student named | 0 | **0** |
| **Step 3b** — every one of the 12 occupations exact | 2 of 2 | **2 of 2** |
| Citations present | every reply | **every reply** |
| `active_skills: ["plain_language"]` on `answer_returned` | — | **5 of 5** |
| Model calls with zero cache hits | 0 | **0** |

**Report the sentence-length median honestly: it did not move.** The brief asked
for it and it is 15.0 → 16.0 on step 2 and 10.0 → 10.0 on step 3b. What changed
is vocabulary and opening shape, and those changed a lot. Toggle off, step 2
run 1 opened:

> Now let me dig into the sections with the highest disengagement… Let me pull
> the section-level engagement for these programs. But first, I need section IDs.
> I don't have a tool to list sections by program… Actually, I don't have a
> `get_my_sections` tool…

Toggle on, the same question:

> Business Administration, BS (BUS-BS) stands out as the program under the most
> strain.
>
> **BUS-BS has the most students who have stopped logging in.** One quarter of
> its students — 25.0% — have not logged in for over ten days [colleague].

Every figure in that reply checks out: BUS-BS 48 students, 12 quiet (25.0%),
63.6% logged in this week, 12 missing submissions, GPA 2.81; HIM-BS 10.4% and
77.4%; CS-BS 95.0% and 16 missing across 3 sections; IS-MS 10 missing, the
lowest. Step 3b's twelve growth rates and twelve median wages were exact in
every run in both arms.

One caution on step 3b: with the skill on, one run volunteered each occupation's
skill list and the programme crosswalk, so the reply got *longer* (161 → 316
median words). Nothing in it was wrong. Plain language is not the same as short.

### 5.4 The finding — the toggle degrades demo moment 5

Not asked for by the brief. Run because "refusal beats unaffected" needed
evidence, and it is the most decision-relevant number in the session.

Five fresh two-turn conversations as noor with `plain_language` active, scored
the same way Session 11 scored them, against four toggle-off runs from arms 1
and 2.

| Measure | Toggle off (4 runs) | Toggle on (5 runs) |
|---|---|---|
| Turn 2 ended in the mcp-canvas refusal with its amber row | **4 of 4** | **3 of 5** |
| Guard fires | 2 in 8 replies | **6 in 10 replies** |
| Declines — the user sees the flat sentence | **0** | **1** |
| Invented section ids | 0 | 0 |

The two misses:

- **Run 2 of window F** (rows 7100, 7104): the guard rejected turn 2 twice and
  declined. The user saw *"I can't ground an answer to that with the tools
  available."*
- **Run 2 of the second batch** (row 7132): turn 2 answered "I don't teach
  BUS-201-A. My sections this term are CYB-210-A and CYB-310-A" from
  `get_my_sections` alone — true, grounded, correctly cited, and no tool refusal
  and no amber row. This is exactly the shape Session 11 named in LESSONS
  entry 12.

A third run relayed a refusal but said something false on the way: *"I cannot
pull engagement for CYB-310 or BUS-201-A because neither section is among your
assigned sections"* — CYB-310-A **is** hers. It had called
`get_section_engagement` with `CYB-310`, an id no tool ever returned, and been
refused for it (rows 7087, 7088). The amber row is there and the sentence is
wrong.

**The mechanism, stated generally:** an instruction block sitting immediately
before the question competes with the question for the model's attention, and
what it displaces first is the decision to go and fetch something. This is
Session 11's coupling finding arriving from the other direction, and it is why
`docs/LESSONS.md` entry 13 says a behavioural skill is a change to the agent
loop, not a change to the stylesheet.

**What was done about it, and what was not.** Nothing was fixed —
the no-fixing-after-measurement rule holds. `DEMO_VERIFICATION.md`'s new
optional-beat section states the constraint in as many words: *do not run demo
moment 5 with the toggle on; the plain-language beat is a prose beat, keep it on
prose.* The toggle ships **off by default** and resets on every new chat session,
so the certified behaviour is what a fresh demo gets.

---

## 6. The freeze certification — rows 7153–7250

One pass, run by the demo-verifier agent, 2026-08-10 00:10:42–00:14:19Z, 98
rows. Configuration verified on the live containers before it started
(`AGENT_THINKING=false`, `SKILLS_ENABLED=true`, `ROUTER_THINKING=false`). Steps
1–10 with no `active_skills` at all, plus **step 2b** — step 2's question with
`active_skills: ["plain_language"]`. Driven through the gateway's `/chat` with
real persona tokens; step 4 via the unmodified bypass script; every figure
recomputed from `data/*.db` and independently checked by a second agent, which
agreed on every value. The verifier changed nothing in the repository.

### 6.1 Result — 13 of 14 pass, one fails

| Step | Verdict |
|---|---|
| 1 | **PASS** — all four counts, **and group membership exact in all three headings** |
| 2 | **PASS** — all 30 aggregates exact, no student named, both servers cited correctly |
| **2b** | **PASS** — every figure exact, no student named, citations present, row **7171** carries `active_skills: ["plain_language"]` |
| 3a / 3b | PASS / PASS |
| 4 | **PASS** — `tools_used: []`, mcp-colleague refusal row **7180** verbatim |
| 5a | PASS |
| 5b | **PASS on both halves** — the spec sentence verbatim, amber row **7192** |
| **5c** | **FAIL** — the rollup is exact; the closing sentence is not |
| 6 | PASS |
| 7 | **PASS — zero arithmetic errors** across every tally and skill enumeration |
| 8 | **PASS** — six distinct `get_course_outcomes` calls before any catalog-wide claim |
| 9 | PASS |
| 10 | PASS — 401 at all six services independently, rows 7245–7250 |

Standing checks, all green except the recomputation one:

| Check | Result |
|---|---|
| Prompt cache | **22** model-call rows, minimum `prompt_cache_hit_tokens` **896**, **zero** calls with zero hits |
| Four spec-fixed refusal strings, verbatim at the tool layer | **All four** (rows 7240–7243), plus the faculty/dean asymmetry on the same call one second apart (7243 refused, 7244 ok) |
| Dropped audit events in the window | **Zero** |
| `tools_used ⊆ tools_offered` | Holds on all **11** `answer_returned` rows; `unoffered_calls` present and empty on every one |
| Every id and code resolves | **Zero unresolved** across all ten captured replies |
| Every stated figure recomputed | **One wrong** — step 5c |
| Guard ledger | **3 fires, 3 regenerations, 0 declines** (7184, 7191, 7198), all canvas-only requests citing `[colleague]` |
| `active_skills` discipline | 2b's row `["plain_language"]`; the other **ten** rows `[]` |

### 6.2 The failure, quoted

Step 5c's eighteen rollup cells and six missing-submission counts are all exact.
The sentence after the table is not:

> "Across all six programs, 78 missing submissions are outstanding."

The true total is **112** — 16 + 24 + 28 + 10 + 22 + 12. **78 is the running sum
of the first four rows of the model's own table**, in the order it printed them;
it stopped adding after four.

### 6.3 Why the fallback was not executed

The brief pre-authorized one fallback: *"if the skills feature causes any step
failure or regression, set `SKILLS_ENABLED=false` in compose, re-run the verifier
once, and ship with the feature dark."* Three facts decide it, and they all point
the same way:

1. **Step 5c ran with the toggle off**, like every step in the pass except 2b.
   Its `answer_returned` row carries `active_skills: []`.
2. **Neither thing built this session touches mcp-canvas.** The membership lists
   are in mcp-colleague; the skill is in the orchestrator and the registry.
   `services/mcp-canvas/` is byte-identical to Session 11's certified state.
3. **The defect class is old and was recorded before this session existed.**
   Session 11 §5.3 found it twice in three runs of step 7 ("0 of 6" for 0 of 7;
   "eight" for seven) and certification pass A found a third instance ("Five
   other occupations" where it is seven). Session 9 finding 9.2 is the same
   class.

Turning `SKILLS_ENABLED=false` would not change that figure by one digit. Running
the fallback would have produced a second pass in a configuration that cannot
affect the failing beat, and — worse — it would have amounted to re-running the
certification until it came back green. **I did not re-run the pass**, for the
same reason. The rule against fixing after measurement begins is worth nothing if
measurement can be repeated until it agrees.

### 6.4 The fix, proposed and not made

`get_program_engagement_rollup` should return `total_sections`,
`total_enrollment` and `total_missing_submissions` beside the per-program rows,
so the model transcribes the total instead of deriving it — with the docstring
saying so, exactly as `get_my_advisees` now does for the membership lists. It is
a small change to `services/mcp-canvas/app.py`, one test, and no seed change.

**Two rules independently prevented it this session**: `services/mcp-canvas/` is
outside the brief's permitted diff ("nothing … in the other three MCP servers"),
and the finding arrived after measurement began. It is the fifth instance of the
pattern that has held every time it has been applied — `docs/LESSONS.md` entry 4
has the tally — and the one number this demo reads aloud that no tool computes.

### 6.5 The verifier's other observations

Recorded in `DEMO_VERIFICATION.md` as W1–W5 and summarised here:

- **Step 2b signs canvas figures `[colleague]`** — "63.6% logged in… 12 missing
  submissions across 4 sections [colleague]". Step 2, the same question without
  the skill, cited both servers correctly, so on this reply the skill made
  attribution worse. The guard cannot catch it: both servers ran, so
  `[colleague]` is a grounded marker. This is Session 11's W2, recurring.
- **Steps 7 and 8 open with visible deliberation** — the Session 9 narration
  leak, now on the synthesis beats rather than on step 2.
- **Step 5b's refusal was again produced by the guard's retry** (row 7191).
  LESSONS entry 12 stands unchanged.
- **Step 4 produced no grey `unoffered` row** this time: the model reached for
  nothing it did not hold. Better behaviour, one fewer colour on the audit page.
- **Seed data needs no change**, and the verifier recommends against one. The
  25/9/8/6 quartet holds and the membership lists closed step 1 without touching
  a row of seed data.

---

## 7. Item 4 — the documents

### 7.1 `DEMO_VERIFICATION.md`

A new section, **"The optional plain-language beat — after 8, before the
receipts"**, placed immediately after the casting table: how to run it (kim,
already in Executive Insights, repeats moment 2's question with the switch on),
what to say out loud, and the two constraints — default off, and never on
moment 5, with the measured numbers behind that.

### 7.2 `docs/LESSONS.md` entry 13

**Skills: behaviour is configuration, and configuration must be governed.** The
four governance properties (registry, RBAC against the caller's own token,
trailing-message injection so the cached prefix survives, `active_skills` in the
audit trail), the measured cost from §5.4 stated as a general lesson, and then
the part written for the MVP team:

| Activation | Whose judgement | What the skill encodes | POC-grounded example |
|---|---|---|---|
| `user` | the person asking | a **choice** | `plain_language` |
| `role-default` | the institution | a **policy** | an adjunct skill requiring every answer to say which figures are public |
| `surface-default` | the product | a **genre** | "one student at a time" in the Advisor Workspace; "programme headline first, no individuals" in Executive Insights |
| `model-invoked` | the model | **know-how** | the skills-matching procedure now sitting in the static prompt and paid for on every request |

One hard rule, stated as a rule: **a policy skill is never model-invoked** — if
the institution decided it, the model does not get a vote on whether it applies,
or the institution's policy has become the model's opinion. Model-invoked skills
are legitimate for know-how under two conditions: **catalog-governed** (the model
chooses when, the registry governs what exists) and **audit-stamped** (the record
says which skill loaded). The POC implements `activation: user` only; the field
is in the registry so the other three are an extension rather than a redesign.

Entry 9 also gains a short paragraph: "ship the group membership too" is no
longer advice, it is built and measured (§3.4).

---

## 8. Deviations from the brief

1. **`services/gateway/app.py` was changed, and it is outside the permitted
   diff.** The brief put `active_skills` on the orchestrator's `/chat` and put
   the toggle in the two Chainlit apps — but the apps post to the *gateway*, and
   the gateway builds the orchestrator's request body field by field. Without
   two lines there, a switch in the UI could not reach the code that reads it.
   The change is a pass-through and nothing else: one field on the request model,
   one key in the forwarded JSON, no validation, no branching, no authorization
   logic. The hard rule it might have threatened — authorization decisions live
   only in the MCP servers plus registry filtering in the orchestrator — is
   intact, because the gateway makes no judgement about a skill any more than it
   makes one about a tool.

2. **`tests/test_skills.py`'s unauthorized case uses a minted token rather than a
   persona.** The brief specified one skill granted to `[advisor, dean, faculty,
   adjunct]`, which is every data role in `config/personas.yaml`, so no persona
   can be unauthorized for it. Rather than add a second skill to the registry
   purely so a test could fail against it, the test mints a correctly signed,
   unexpired, correctly-audienced token carrying `roles: ["registrar"]` — the
   technique `tests/test_auth.py` already uses for its claim-level cases. No
   check is weakened anywhere.

3. **Demo moment 5 was measured with the toggle on, which the brief did not
   ask for.** The brief's toggle-on arm was step 2 ×3 and step 3b ×2, and it
   required "refusal beat unaffected" — a claim neither of those beats can
   support, because neither contains a refusal. Five runs of moment 5 were added
   to test it directly. They found the session's most important result (§5.4).

4. **`docs/patches/README.md` and `docs/LESSONS.md` entry 12 already existed.**
   Session 11 wrote both, and both already said what the brief asked for. They
   were extended rather than duplicated (§2.1, §2.2).

5. **`DEMO_VERIFICATION.md` has no script listing to update**, so the optional
   beat went in as its own section after the casting table. The script itself
   lives in `SPEC.md` §7, which is not in the permitted diff.

6. **A `skill_refused` row renders green on the audit page**, and this was left
   alone. `services/audit/viewer.html` colours a row by its `detail.decision`
   field, and the orchestrator's `skill_refused` detail carries `skill`,
   `reason`, `requested` and `latency_ms` but no `decision` — so a refusal reads
   as a success on the receipts page. The fix is one key —
   `"decision": "refused"` in that audit call — and it needs no change to
   `services/audit/`, which the brief forbids. **It was found after measurement
   began and was therefore not applied.** It affects no demo beat: nothing in
   the script activates an unauthorized skill.

---

## 9. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 0 | `docs/patches/` holds both patches; a README saying what each is, that item2 applies cleanly to `0e08b1c` with five passing tests, why it was reverted, and the recommended MVP variant | **PASS.** Both patches present. The README existed; it gained the passing-test count, the unmeasured MVP variant, and three repointed references. §2.1 |
| 1 | LESSONS entry 12 — an enforcement receipt must never depend on the model volunteering; generate it deterministically, the bypass script being the pattern | **PASS, and it already existed.** Session 11 wrote exactly that entry. Left in place, reference repointed. §2.2 |
| 2 | `get_my_advisees` returns `flagged_ids`, `quiet_ids`, `flagged_and_quiet_ids` from the same rows it ships; docstring extended; no prompt changes | **PASS.** §3.1. `services/orchestrator/prompts.py` is byte-identical to HEAD |
| 3 | One test: each list's length equals its count and its members match the filtered rows | **PASS.** §3.2 |
| 4 | One seed `verify()` line: the three lists consistent with the 25/9/8/6 cast | **PASS**, green on the first run with nothing retuned. §3.3 |
| 5 | Measure step 1 ×5: every student in the right group, zero self-contradiction, counts verbatim | **PASS — 5 of 5 on all three.** §3.4 |
| 6 | `config/skills.yaml`: one skill, `plain_language`, four roles, `activation: user`, description, instructions with the facts/numbers/citations/refusals carve-out | **PASS.** §4.1 |
| 7 | Orchestrator `/chat` accepts `active_skills`; validated against registry and roles; unauthorized or unknown refused courteously and audited; injected as ONE trailing message after the prefix and before the question; `answer_returned` gains `active_skills` | **PASS.** §4.1 |
| 8 | Feature-gated on `SKILLS_ENABLED` (compose, default true); when false nothing is rejected or ignored, the field is absent from the UI and unused, behaviour byte-equivalent | **PASS**, and measured as arm 1: not one row in a 38-row window mentions skills. §5.1 |
| 9 | Both apps: a settings switch, default off, shown only when `SKILLS_ENABLED`; session passes `active_skills`; subtle indicator when on | **PASS**, proven over the real socket.io path, not by inspection. §4.1 |
| 10 | Tests: unauthorized skill refused, unknown skill refused, authorized skill accepted, audit field present and correct | **PASS — three tests.** The unauthorized case uses a minted valid token with an ungranted role; §8 deviation 2 says why |
| 11 | Kill-switch regression, `SKILLS_ENABLED=false`: step 1 ×2, moment 5 ×2, bypass ×1, indistinguishable, no skills field anywhere | **PASS.** §5.1 |
| 12 | `SKILLS_ENABLED=true`, toggle off: the same three, identical again | **PASS.** §5.2. The only difference is an empty `active_skills` field |
| 13 | Toggle on as kim, step 2 ×3 and step 3b ×2: register visibly changes with sentence-length medians reported, figures exact, citations present, refusal beat unaffected, `active_skills` on every row | **PARTIAL.** Figures exact 5 of 5, citations present 5 of 5, `active_skills` on 5 of 5. **The sentence-length median did not move** (15.0 → 16.0; 10.0 → 10.0) and is reported as measured; vocabulary and opening shape moved a great deal. **"Refusal beat unaffected" is not met** — neither beat contains a refusal, so it was tested directly on moment 5, and the answer is no. §5.3, §5.4 |
| 14 | Cache check across all arms: zero zero-hit calls | **PASS.** Minimum `prompt_cache_hit_tokens` 896 in every arm and in the certification pass; zero calls at zero |
| 15 | One full demo-verifier pass, steps 1–10, toggle off, plus a step 2b with content parity and changed register | **RUN, AND IT FAILED A STEP.** 13 of 14 pass. **2b passes.** 5c fails on one derived figure. §6 |
| 16 | FALLBACK if the skills feature causes any step failure or regression | **NOT TRIGGERED, and the reasoning is in §6.3.** The failing step ran with the toggle off, in a service this session did not touch, on a defect class recorded three times before this session |
| 17 | `pytest` green, 137+ | **PASS — 137 passed.** §10 |
| 18 | Certification 10/10 plus a passing 2b (or the fallback executed and certified dark) | **NOT MET.** 13 of 14 with 2b passing; step 5c fails. Neither branch of this criterion is satisfied, and §6.3 explains why the second branch would have been dishonest rather than corrective |
| 19 | Diff confined to the named paths | **ONE EXCEPTION** — `services/gateway/app.py`, two lines of pass-through, without which the UI toggle cannot reach the code that reads it. §8 deviation 1. Everything else is inside the list |
| 20 | DEMO_VERIFICATION script gains the optional plain-language beat; LESSONS entry 13; commit | **PASS.** §7. The beat carries the measured constraint from §5.4 |

---

## 10. Evidence — the suite and the pre-demo check

```
$ uv run pytest tests/ -q
137 passed
```

133 before this session, plus one membership test and three skills tests. No test
was removed or weakened.

The pre-demo check, run **after** the suite as `CLAUDE.md` instructs. One drop in
the half-hour view, and it is the disruptive test — a third of a second after
that test stops the audit container on purpose:

```
$ docker compose logs --since 30m --timestamps 2>&1 | grep -E "dropped|Shutting down"
audit-1    2026-08-10T00:24:30.540Z INFO:     Shutting down
gateway-1  2026-08-10T00:24:30.876Z audit event 'auth_failed' dropped ...
```

The certification pass ran 00:10:42–00:14:19, ten minutes before that shutdown,
and the verifier independently confirmed zero drops inside its own window. **The
receipts demo moment 9 points at are complete.**

`tests/test_ui_apps.py` still fails if the two copies of `harness_chat.py` drift,
and they do not:

```
$ md5sum apps/*/harness_chat.py
af2aed6942f1fd0b99bf895e53432737  apps/ui-advisor/harness_chat.py
af2aed6942f1fd0b99bf895e53432737  apps/ui-exec/harness_chat.py
```

### Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-11.md && git commit          # d77a2f5

# item 1
uv run scripts/seed.py                                                # verify() green, first attempt
docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
uv run pytest tests/test_tool_results.py -q                           # 8 passed
uv run --with httpx python ask.py dana "Which students seem to be struggling this term?" 5 step1.json

# item 2
docker compose up -d                                                  # SKILLS_ENABLED=true
uv run pytest tests/test_skills.py -q                                 # 3 passed
uv run pytest tests/ -q                                               # 137 passed

# arm 1 — the kill switch
echo SKILLS_ENABLED=false >> .env && docker compose up -d
docker inspect harness-poc-orchestrator-1 harness-poc-ui-advisor-1 | grep SKILLS
uv run --with httpx python warm.py
uv run --with httpx python ask.py dana "…struggling…" 2 a1-step1.json
uv run --with httpx python moment5.py 2 a1-moment5.json
./scripts/demo_bypass.sh                                              # rows 6940-6941

# arm 2 — the feature on, the toggle off
sed -i 's/^SKILLS_ENABLED=false$/SKILLS_ENABLED=true/' .env && docker compose up -d
# …the same three…                                                    # rows 6966-7004

# the toggle on
uv run --with httpx python ask.py kim "…struggling…"        3 off-step2.json
uv run --with httpx python ask.py kim "…growing fastest?"   2 off-step3b.json
uv run --with httpx python ask.py kim "…struggling…"        3 on-step2.json  '["plain_language"]'
uv run --with httpx python ask.py kim "…growing fastest?"   2 on-step3b.json '["plain_language"]'
uv run --with httpx python moment5.py 5 on-moment5.json              '["plain_language"]'

# the surface path, over real socket.io
uv run --with httpx --with "python-socketio[asyncio_client]" python uitoggle.py   # rows 7255, 7260

# the certification
# the demo-verifier agent, steps 1-10 plus 2b                          # rows 7153-7250

# acceptance
uv run pytest tests/ -q
docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
```

Scratchpad helpers (`ask.py`, `moment5.py`, `warm.py`, `score.py`, `m5score.py`,
`lens.py`, `register.py`, `uitoggle.py`) and the run transcripts are throwaway;
nothing in the repository depends on them. The verifier's own artefacts —
`runs.jsonl`, the ten captured replies, the 98-row window dump and its
independent ground-truth recomputation — are beside them.

---

## 11. Open questions

1. **Step 5c's total is the one thing standing between this and a clean
   freeze**, and the fix is known, small, and of the shape that has worked five
   times: return `total_missing_submissions` (and the two other totals) from
   `get_program_engagement_rollup`. Two rules stopped me making it — mcp-canvas
   is outside the permitted diff, and the finding arrived after measurement
   began. It wants one short session: the change, one test, a re-seed-free
   restart, and one verifier pass.

2. **Ship the toggle on, or dark?** Arms 1 and 2 say the feature costs nothing
   when the switch is off, and the switch is off by default and resets each
   session. §5.4 says the switch itself is not free on the one beat that carries
   the RBAC story. The constraint in `DEMO_VERIFICATION.md` — use it on step 2,
   never on moment 5 — is documented, not enforced. If you want it enforced, the
   honest version is `SKILLS_ENABLED=false` in `.env` on the demo machine, and
   everything else in this session stands unchanged.

3. **A `skill_refused` row renders green on the audit page**, §8 deviation 6.
   One key in one audit call, no change to `services/audit/`.

4. **Step 2b cited canvas figures `[colleague]`** where step 2, the same
   question without the skill, cited both servers correctly. One reply is not a
   finding, but if the plain-language beat is going into the demo it is worth
   five more runs to know whether the skill makes attribution worse.

5. **Nothing beyond the archive commit is committed** at the time of writing;
   the commit follows this report.
