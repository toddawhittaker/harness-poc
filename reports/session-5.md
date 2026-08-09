# SESSION_REPORT — harness-poc Session 5

The final pre-demo pass. Six changes, then measure. Nothing structural.

This report stands alone. It quotes the commands run and their output, because
the person reading it has no access to the terminal it was written from.

**Headline:** all six changes are done. `uv run pytest tests/ -q` reports **122
passed** (117 before). The demo-verifier ran SPEC §7 steps 1–10 through the real
Chainlit apps and returned **eight clean passes, one pass-with-warts, and one
FAIL**. The FAIL is step 5b, and it is the one thing in this report that needs a
decision before the demo: in **3 of 10 runs the model fabricates BUS-201-A
engagement data** — invented students, invented numbers — with no tool call and
no audit row. The seed change removed the cause Session 4 blamed and the failure
survived it, so the cause was something else.

Four of the five prompt- and seed-driven Session 4 findings closed. The step-7
tallies are now exact 3 of 3; the invented program codes are gone 3 of 3; two of
the three citation findings closed; the possessive removal closed the step-2
narration problem for both personas. Section 4 says exactly where the rest
stand.

The verifier's full record is in `DEMO_VERIFICATION.md`, at the top, and the
Session 4 section beneath it is retitled as superseded.

---

## 1. Acceptance status per criterion

| # | Criterion (from the brief) | Status |
|---|---|---|
| 1 | `pytest` green, >117 with the parametrized extension | **PASS** — 122 passed in 31.51s |
| 2 | Verifier clean of Session 4's §7.3 findings | **PARTIAL** — see the table in §4.1. Counting: closed on step 7, open on steps 1 and 8. Citations: two of three closed, one improved. Seed adjacency: removed, but the failure it was blamed for survived. Program-code guessing: closed |
| 3 | Steps 1–10 pass | **9 of 10 PASS, step 5b FAILS** — §4.2 |
| 4 | Diff confined to the named files | **PASS with one disclosed extension** — three `services/mcp-*/app.py` files, two lines each. §3 |

Change 6's own instruction — "NO further prompt iteration this session" — was
followed. No prompt was touched after the two commissioned edits (changes 2 and
3), including when the verifier's findings pointed straight at one.

---

## 2. What was done

Session start: `SESSION_REPORT.md` was moved to `reports/session-4.md` and that
move was committed by itself as **`27b8aa3`**, per `CLAUDE.md`. It is the only
commit made this session.

### 2.1 Change 1 — the question loses its possessive, for both personas

`SPEC.md` §7 steps 1 and 2, `apps/ui-advisor/app.py`, `apps/ui-exec/app.py`.

Both starter buttons now send the identical string, verbatim:

```
Which students seem to be struggling this term?
```

SPEC §7's wording, minimally updated so the expected answers match the new
question:

```
1. Both UIs side by side. Dana in Advisor Workspace: *"Which students seem to be
   struggling this term?"* → her 25 — the only students her tools reach — the
   quiet ones flagged, cited `[colleague]`.
2. Kim in Executive Insights, **the same words** → program aggregates, no
   individual names. The question carries no possessive, so neither answer has
   to argue with it; the role alone decides the scope. Same harness, same second.
```

Pat's step 3 beat is unchanged in the spec and unchanged in behaviour.

One label changed with it: the advisor app's button read "Struggling advisees",
which stops being honest once the question is about students, so it now reads
"Who is struggling" — the same label the exec app already used. The two apps
still differ in every other starter, in title, greeting, and theme.

**The risk this carried, and how it was retired before anything else was built.**
The gateway's router lists `program_aggregate` as plausible for dean and faculty
and **not** advisor. "Which students seem to be struggling this term?" reads as
plausibly aggregate, so dana could have been refused at the gate — breaking step
1 outright. The gateway is outside this session's diff, so a fix there was not
available. I measured it first, three runs, before touching anything else:

```
=== dana run 1 ===  {"status": 200, "tools_used": ["get_my_advisees"]}
=== dana run 2 ===  {"status": 200, "tools_used": ["get_my_advisees"]}
=== dana run 3 ===  {"status": 200, "tools_used": ["get_my_advisees"]}
```

Routed through, 3 of 3, and the verifier later got 3 of 3 again through the UI.
Kim routes through and pat is still refused at the gate, both confirmed in the
same probe. The risk did not materialise.

### 2.2 Changes 2 and 3 — `services/orchestrator/prompts.py`

`SYSTEM_PROMPT` is still one triple-quoted literal. Verified by AST after every
edit (§5.1). It grew from 5161 to 6334 characters.

**(2a) The counting constraint**, added to the Style paragraph rather than to
rule 5, because Session 4's worst counting error was on step 1 — "Five of your
advisees are clearly struggling", then nine named — which rule 5 does not
govern:

> Any count you state must equal the number of items you name beside it: count
> the names, write that number, and never let a tally contradict its own list. A
> remainder is the total minus the number you named, and a coverage count is the
> length of the covered list you then give. If the number and the list disagree,
> the list is right — recount before you write.

**(2b) Program codes are never guessed**, added to the end of rule 5:

> Program codes are never guessed. Before any `get_course_outcomes` call,
> resolve the code with `list_programs_catalog` in this run and use a code that
> call returned; if that tool is not available to you, use only a code already
> in front of you in the question or in another tool result, and invent one in
> no circumstances.

The middle clause is a deliberate departure from the brief's literal wording,
and it is load-bearing. `config/registry.yaml` gives `list_programs_catalog` to
**dean only**; the `faculty` role holds `get_course_outcomes` without it. An
unqualified "always call `list_programs_catalog` first" would be an instruction
noor cannot obey, and the observable result would be the model narrating about a
tool it cannot see — the exact failure mode Session 4 spent four iterations
closing. The clause keeps the prohibition absolute and makes the procedure
conditional.

**(3) Rule 2, rewritten.** The old rule defined markers by subject matter, and
the model read "program-level anything" as curriculum. The new rule defines them
by origin:

> 2. Cite every fact inline, and let the marker name the server whose tool
>    returned that fact — not what the fact happens to be about. [colleague] for
>    what mcp-colleague returned: student records, degree progress, enrollment,
>    and program enrollment summaries. [canvas] for what mcp-canvas returned:
>    this week's engagement and section activity, including program-level
>    engagement rollups. [kuali] for what mcp-kuali returned: curriculum and
>    course outcomes, and nothing else. [labor] for what mcp-labor returned:
>    occupations, wages, growth, and the program-to-occupation crosswalk. A
>    number about programs is not [kuali] for being about programs; it carries
>    the marker of the server that produced it. A sentence drawing on two servers
>    carries both markers. When you relay a refusal, cite it to the server that
>    refused.

The ground rules stay at five and the unnumbered reply-shape block is untouched,
so every external reference to "rule 3" and "rule 5" still reads true.

### 2.3 Change 4 — `scripts/seed.py`, noor's second section

Two instructor columns swapped, and nothing else in the file's data:

```python
-    ("BUS-201-B", "BUS-201", "noor", "Noor Haddad"),
+    ("BUS-201-B", "BUS-201", "fac-005", "Denise Crawford"),
-    ("CYB-210-A", "CYB-210", "fac-004", "Alan Petrov"),
+    ("CYB-210-A", "CYB-210", "noor", "Noor Haddad"),
```

Section ids, their order in `SECTIONS`, and the round-robin that fills them are
untouched, so no student's enrolment or activity row moved. BUS-201-B is still
seeded visibly unhealthy; it simply belongs to fac-005, who already held
BUS-201-A.

`verify()` gained the guard the brief asked for, plus the sentence explaining
why it exists:

```python
noor_sections = [sid for sid, _course, sub, _name in SECTIONS if sub == "noor"]
assert len(noor_sections) == 2, (
    f"SPEC §3 says noor teaches two sections; she has {noor_sections}")
noor_bus = [sid for sid in noor_sections if sid.startswith("BUS-")]
assert not noor_bus, (
    f"noor must hold no BUS section, and she holds {noor_bus}. Demo moment 5 "
    "asks her about BUS-201-A and needs the tool refusal to fire; a BUS "
    "section of her own gives the model something adjacent to answer about "
    "instead. Give her a section outside the BUS prefix.")
```

Re-seeded, and the four MCP servers restarted per `CLAUDE.md`:

```
$ uv run scripts/seed.py
verified:
  dana advises 25, of whom 8 have not logged in for >10 days
  demo moment 6 asks about S-1055 (Leon Cline, CS-BS)
    taking now: CS-210 / next term: CS-310, CS-350, CS-410 / blocked: CS-460
  S-1042 keeps his own answer: nothing new next term, 1 blocked
  noor teaches CYB-310-A, CYB-210-A and no BUS section
  CYB-BS vs Information Security Analysts: 8/8 skills (strong)
  CYB-BS vs Network/Systems Administrators: 3/6 (partial)
  CYB-BS vs Data Scientists: 0/7 (miss)
  unmapped fast-growers: AI/ML Engineers, Cloud Infrastructure Architects

$ docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
$ sqlite3 data/canvas.db "select instructor_sub, section_id from faculty_assignments
                          where instructor_sub='noor' or section_id like 'BUS-201%'"
fac-005|BUS-201-A
fac-005|BUS-201-B
noor|CYB-210-A
noor|CYB-310-A
```

**The brief's acceptance for this change — "confirm demo moment 5 refuses 3 of
3" — is not met.** §4.2 has the measurement and the reason.

### 2.4 Change 5 — the three-tier classification, stamped into three servers

`services/mcp-canvas/rules.py`, `services/mcp-colleague/rules.py` and
`services/mcp-labor/rules.py` now carry mcp-kuali's shape exactly:

| Tier | Caught | `decision` | `reason` | Tool reply |
|---|---|---|---|---|
| a | `ToolError` — the refusals `refuse()` raises on purpose | `refused` | `str(exc)` | the refusal, relayable |
| b | the server's own `Unknown*(ValueError)` | `error` | the message, naming the argument | the same text |
| c | `Exception` catch-all | `error` | `type(exc).__name__` **only** | a fixed `INTERNAL_ERROR` string |

Each server names its own tier-b class and message, in the same shape as
mcp-kuali's `UnknownProgram` / `unknown program code <x>`:

| Server | Class | Message | Raise site |
|---|---|---|---|
| mcp-canvas | `UnknownSection` | `unknown section id <x>` | `services/mcp-canvas/app.py:137` |
| mcp-colleague | `UnknownStudent` | `unknown student id <x>` | `services/mcp-colleague/app.py:154` |
| mcp-labor | `UnknownOccupation` | `unknown SOC code <x>` | `services/mcp-labor/app.py:85` |

Tier (c) raises `ToolError(INTERNAL_ERROR) from exc` directly rather than
`refuse(...)` — Session 4's late correction on mcp-kuali, carried across so the
four files stay one shape.

**`UnknownStudent` is unreachable from outside, deliberately, and its docstring
says so.** `require_assignment` runs before the register is read, so an id
belonging to nobody comes back as "not among your assigned advisees" rather than
confirmed absent; the tools never double as a way to probe which ids exist. That
is the right trade and I did not change it. What is left for `UnknownStudent` is
the genuine fault it describes — an assignment row pointing at a student who is
not in the register.

**Tests.** The two finding-4 tests became two parametrized tests plus one
structural guard, taking the suite from 117 to 122:

- `test_a_bad_argument_audits_as_an_error_not_a_refusal` — three cases:
  mcp-kuali (kim, `ZZZ-XX`), mcp-canvas (kim, `ZZZ-999-Z`), mcp-labor (pat,
  `99-9999`).
- `test_a_role_refusal_still_audits_as_refused` — three cases: mcp-kuali (pat),
  mcp-canvas (pat), mcp-colleague (pat). The negative control: `error` existing
  must not have eaten `refused`.
- `test_every_mcp_server_tells_the_caller_the_same_thing_when_it_faults` —
  reads the four `rules.py` files and asserts one `INTERNAL_ERROR` sentence
  across all of them, in the spirit of the existing byte-identity check on the
  four `mcp_auth.py` copies.

**Two of the eight cells do not exist, by design, and the test file says why
rather than skipping quietly.** mcp-colleague has no reachable bad argument (see
above); mcp-labor refuses nobody, because SPEC §4.5 gives its data to every
authenticated role. Every server appears in at least one of the two tests. This
is a departure from "parametrize across all four servers" taken literally, and
manufacturing the missing cells would have meant weakening a boundary or
inventing a refusal the spec does not want.

One test-harness fix was needed and is worth recording: matching an audit row on
`(service, event, sub, tool)` was not specific enough, because
`test_dean_may_read_the_same_section_the_faculty_member_could_not` calls the
same tool on the same server as the same persona a second earlier. The matcher
now also compares `args_hash`, re-derived independently in the test file so a
change to how the digest is computed fails a test rather than passing silently.

### 2.5 One SPEC §5 sentence, prompted by change 4 and by the verifier

`SPEC.md` §5's Canvas paragraph said "noor teaches CYB-310-A and BUS-201-B". The
seed now says otherwise, and `CLAUDE.md` says the spec wins on conflict, so
leaving it would have planted the same trap Session 3's finding 2 found. Three
edits to that paragraph: the instructor list, the reason noor must hold no
adjacent id, and the texture clause the verifier flagged as stale (the clause
implied BUS-201-B was hers). BUS-201-B is still specified visibly unhealthy,
because it still is.

---

## 3. The diff

```
 DEMO_VERIFICATION.md             | 763 ++++++++++++++++++++++++++++++++++++++-
 SPEC.md                          |   6 +-
 apps/ui-advisor/app.py           |   4 +-
 apps/ui-exec/app.py              |   2 +-
 scripts/seed.py                  |  32 +-
 services/mcp-canvas/app.py       |   4 +-
 services/mcp-canvas/rules.py     |  37 +-
 services/mcp-colleague/app.py    |  10 +-
 services/mcp-colleague/rules.py  |  48 ++-
 services/mcp-labor/app.py        |   4 +-
 services/mcp-labor/rules.py      |  41 ++-
 services/orchestrator/prompts.py |  34 +-
 tests/test_auth.py               | 199 +++++++---
 13 files changed, 1095 insertions(+), 89 deletions(-)
```

Plus this file. `data/*.db` is gitignored and was regenerated, as the brief
allows.

**The one disclosed extension.** The brief's diff list names "the three named
rules.py files". Three `services/mcp-*/app.py` files also changed, two lines
each — an import and one `raise`:

```python
-    raise ValueError(f"no section {section_id}")
+    raise UnknownSection(f"unknown section id {section_id}")
```

This is not optional. The whole point of the change is that the tiers are told
apart by exception **type** and never by message text, and a type can only be
distinguished if the raise site uses it. Session 4 hit the identical wall on
`services/mcp-kuali/app.py` and the user amended it into scope during planning;
this is the same amendment for the other three. Nothing else in those files
moved.

Everything else is inside the permitted list. `git status --short` on
`libs/`, `services/identity-stub/`, `services/audit/`, `services/gateway/`,
`services/orchestrator/app.py`, `config/`, `docker-compose.yml`, `.env.example`,
`CLAUDE.md` and `ARCHITECTURE.md` is **empty**.

---

## 4. What the verifier found

Full record in `DEMO_VERIFICATION.md`. Run 05:03:58–05:09:58 UTC through the
real Chainlit apps over socket.io, `./scripts/demo_bypass.sh` unmodified for step
4, audit rows 3021–3269. Nothing in the repository changed during the run.

### 4.1 The five Session 4 findings this session aimed at

| Session 4 finding | Change | Outcome |
|---|---|---|
| Counting errors (steps 1, 7, 8) | 2a | **Closed on step 7** — every tally in all three runs exact, checked against the databases. **Open on steps 1 and 8** |
| Citation markers (steps 5b, 5c, 7) | 3 | **5c closed** (was 11 of 11 wrong, now 0). **7 closed** (crosswalk now `[labor]`). **5b improved, not closed** — 3 of 7 still `[colleague]` |
| Model guesses program codes (step 7) | 2b | **Closed, 3 of 3.** `list_programs_catalog` fires first every time; zero mcp-kuali error rows in the whole script |
| Seed adjacency (step 5b) | 4 | **Adjacency removed, failure survived.** §4.2 |
| Catch-all-as-refusal in three servers | 5 | **Closed.** Verified live on all four servers, rows 3205–3213 |

Two things the verifier reports as **regressions** that no change this session
touched, both on step 8: the "missing everywhere" over-claim Session 4 closed is
back (the model claimed a skill is taught in no program after fetching four of
six), and a count contradicts its own list ("Three skills are missing…" followed
by two). The counting constraint took on step 7 and not on step 8.

### 4.2 Step 5b — the FAIL, and it is a fabrication

The verifier ran it **ten** times rather than the five I asked for, on the
grounds that five samples cannot separate a 20% failure rate from a 40% one.

| Outcome | Count |
|---|---|
| `get_section_engagement` called, mcp-canvas `refused` row written, refusal relayed | **7 of 10** |
| No tool called, no audit row, **BUS-201-A engagement data invented** | **3 of 10** |

Rows 3188–3196, 3232–3234 and 3255–3256 are each an `answer_returned` with
`"tools_used": []` and no mcp-canvas row beside them. Verbatim from run 5:

> BUS-201-A is in rough shape. Only **13 of 24 students are active this week
> (54%)** [colleague], and there are **35 missing submissions** across the class
> [colleague].
>
> **Most at risk (7+ missing, not active):**
> - John Lee — 0 of 3 submitted, 3 missing, last login 10 days ago [canvas]
> - Taylor Abdeljawad — 0 of 3 submitted, 3 missing, last login 9 days ago [canvas]

It named 24 students in three tiers. The real BUS-201-A, pulled with kim's
token, has **three**:

```
enrollment 3, pct_logged_in_this_week 66.7, missing_submissions 2
  S-1015 Patrick Stanton  last_login 0d  submitted 7  missing 1
  S-1023 Olivia Dawson    last_login 8d  submitted 7  missing 1
  S-1147 Tyler Hendricks  last_login 1d  submitted 8  missing 0
```

Not one name or number matches. This is invention, not leakage — the better of
the two bad outcomes — but on the slide whose entire point is that the boundary
holds, the room watches a faculty member being handed another section's roster,
and demo moment 9 has no amber row to point at.

**I found this before the verifier did**, measuring change 4 over eight runs
through the gateway: 5 of 8 wrote the refusal row, and one of the three misses
fabricated (audit row 2807, 04:54:17). I reported it in-session rather than
acting on it.

**What the seed change did and did not do.** It removed the adjacency Session 4
blamed — noor now holds CYB-310-A and CYB-210-A and no BUS section, asserted by
`verify()` — and the specific Session 4 symptom, answering about BUS-201-B
instead, is gone. The rate moved from 5 of 8 to 7 of 10. But the failure was
never really about the adjacent id: the model declines to call
`get_section_engagement` because it has already seen from `get_my_sections` that
BUS-201-A is not noor's, and having declined to call it, it sometimes invents
rather than stops. **The adjacency was a contributing cause at most.**

The verifier's assessment of the remaining levers, which I agree with:
`config/registry.yaml` cannot force a tool call, so this is not fixable by
configuration. The three real options are a prompt sentence (barred this
session), a tool-shaped answer (a faculty tool that returns "not yours" as data
rather than as an exception, which is a design change, not a demo fix), or
re-casting the beat. **This is question 1 in §7.**

### 4.3 Step 2 with the new wording — the change that worked

Six answers, three per persona, deliberation counted by script rather than
eyeballed.

| Persona | Run | Total words | Deliberation before the first substantive line | Closing offer? |
|---|---|---|---|---|
| dana | A | 259 | **0** | No |
| dana | B | 280 | **0** | No |
| dana | C | 343 | **0** | No |
| kim | A | 238 | **0** | **Yes** |
| kim | B | 284 | **0** | No |
| kim | C | 250 | **0** | **Yes** |

Kim's openings, verbatim:

> A: Here's what the program-level data shows for this term.
> B: Here's what I can see at the program level:
> C: Three programs stand out as needing attention this term: **Business
>    Administration (BUS-BS)**, **Information Systems (IS-MS)**, and **Data
>    Analytics (DAT-MS)**.

**None of the six answers opens with a limitation at all**, and kim's openings
are now indistinguishable in shape from dana's. Compare Session 4's best
measured behaviour, where two of four spot-check runs still opened with "I don't
have access to advisor-student relationships, so I can't identify your specific
advisees…". The verifier's judgement: "This is the cleanest result in the run."

**Zero individual students named in kim's three answers**, checked by script
against all 300 names in `data/colleague.db` and against the `S-\d{4}` pattern.
SPEC §7.2 holds. Every aggregate figure was checked against the two tools and is
correct.

**Finding 7, the closing offer: improved, not closed — 2 of 3 for kim, 0 of 3
for dana.** It has also changed shape, from "supply student IDs" to "supply a
section ID":

> A: If you want me to drill into a particular section to see per-student
>    engagement, I'd need the section ID.
> C: If you'd like me to drill into particular sections in any of these
>    programs, you can supply a section ID.

Session 4's second run had this in 3 of 3, and its own post-fix spot check had it
in 3 of 4.

### 4.4 Step 7 — the tallies are fixed, the narration is worse

| Run | Total words | Words before the answer line | Closing offer? |
|---|---|---|---|
| A | 631 | **445 (71%)** | No |
| B | 237 | **51 (22%)** | No |
| C | 329 | **196 (60%)** | No |

Every tally in every run is correct, checked by exact-string intersection
against `data/kuali.db` and `data/labor.db` — twelve occupations in run A, all
✓, including the two Session 4 got wrong (Cloud Infrastructure Architects is 2
of 7, not 3 of 7; Financial Analysts is 0 of **6**, not 0 of 5). No
self-contradicting tally anywhere. Every named missing-skill list is correct.
The strong/partial/miss trio lands in all three runs.

The openings all use a form the reply-shape block bans by name:

> A: Now let me match the CYB-BS skills against the fast-growing occupations.
> B: Now I have what I need. Let me match the CYB-BS skills against each occupation.
> C: Now I have the CYB-BS skills covered and the skill profiles of the top occupations. Let me match them.

Session 4 measured 271 of 426 words (64%) and judged step 7 unshippable. **Run A
is worse: 445 of 631, 71%.** Run B is much better at 51 of 237. The variance is
the story — the shape is unchanged and the length is a coin toss.

**Per the brief, I did not iterate. This is question 2 in §7, and the evidence
above is what the call rests on.**

### 4.5 Everything else

- **Step 1** PASS 3 of 3 on the claim, zero narration, `[colleague]` throughout,
  only dana's own students named. Two stated totals are wrong (verifier finding
  7): "your 23 advisees" when she has 25, and "7 of whom also have a GPA below
  3.0" when all nine do.
- **Step 3a** **PASS — was FAIL.** Names advisors and faculty, no deans. Session
  4's re-opened finding 3 is closed.
- **Step 4, the bypass** PASS. Row 3079: `mcp-colleague`, `decision: refused`,
  `get_my_advisees requires the advisor role.`
- **Step 5a** PASS 10 of 10. **Step 5c** PASS, and every citation now correct —
  the eleven-out-of-eleven `[kuali]` defect is gone. **Step 6** PASS.
- **Step 8** PASS on the claim; both unmapped fast-growers surface with
  adjacency. Two grounding/counting defects, above.
- **Steps 9 and 10** PASS.
- **Prompt-cache discipline** PASS — 48 model calls, minimum
  `prompt_cache_hit_tokens` 896, not one call reporting zero hits.
- **Zero audit events dropped during the run.** Step 9's receipts are complete.
- **Zero grey error rows during the ten-step script** — a direct consequence of
  change 2b. Session 4 got one on the flagship slide in both of its step-7 runs.

The verifier also raised four smaller new findings I have not acted on: a
fabricated data source on step 3b ("All figures are from BLS projections via
Lightcast" — mcp-labor returns no provenance field), `mcp-labor`'s `refuse()`
being dead code, `SPEC.md:142`'s refusal example naming an id no call can
produce, and step 6 speculating about a prereq it did not check. All are in
`DEMO_VERIFICATION.md` with the file and change each needs.

---

## 5. Evidence

### 5.1 Static prompt prefixes, by AST

Run after every prompt edit. `CLAUDE.md`'s hard rule and SPEC §1 require these
to be plain constants; nothing in the committed suite checks it.

```
$ python3 -  # assert the module-level assignment's value is a single ast.Constant str
SYSTEM_PROMPT: STATIC, 6334 chars
ROUTER_PROMPT: STATIC, 2619 chars
```

Confirmed independently by the verifier: 48 model calls, zero with zero cache
hits.

### 5.2 The suite, and the invariants

```
$ uv run pytest tests/ -q
122 passed in 31.51s

$ md5sum services/mcp-*/mcp_auth.py | awk '{print $1}' | sort -u
937c7753d32da38d1f44f5c505ab3d51        # one hash, four files — byte-identity holds
```

The 117 → 122 arithmetic: two tests removed, six parametrized cases and one
structural guard added.

### 5.3 The tiers, live on all four servers

Provoked over MCP with real tokens, rows 3205–3213:

| Server | Genuine refusal | Bad argument |
|---|---|---|
| mcp-canvas | noor → `get_section_engagement("BUS-201-A")` → `refused` (3208) | kim → `get_section_engagement("ZZZ-999-Z")` → `error`, `unknown section id ZZZ-999-Z` (3209) |
| mcp-kuali | pat → `get_course_outcomes("CYB-BS")` → `refused` (3213) | kim → `get_course_outcomes("ZZZ-XX")` → `error`, `unknown program code ZZZ-XX` (3210) |
| mcp-labor | no refusal path exists (SPEC §4.5) | pat → `get_occupation("99-9999")` → `error`, `unknown SOC code 99-9999` (3211) |
| mcp-colleague | pat → `get_my_advisees()` → `refused` (3205) | unreachable by design — dana → `get_student_summary("S-9999")` audits `refused` (3212) |

### 5.4 The four spec-fixed refusal strings, verbatim at the tool layer

Rows 3205–3208, all four word for word against SPEC §4.4 and §4.6:

```
 3205 mcp-colleague  pat   get_my_advisees        "get_my_advisees requires the advisor role."
 3206 mcp-colleague  dana  get_student_summary    "Student S-1200 is not among your assigned advisees."
 3207 mcp-colleague  kim   get_student_summary    "Individual student records require an advisor assignment; deans receive aggregates."
 3208 mcp-canvas     noor  get_section_engagement "Section BUS-201-A is not among your assigned sections; cross-section views belong to the dean."
```

### 5.5 The pre-demo check

Run after the suite, as `CLAUDE.md` instructs:

```
$ docker compose logs --since 30m 2>&1 | grep "dropped" || echo "clean"
gateway-1 | audit event 'auth_failed' dropped: POST http://audit:8030/events failed (ConnectError)
```

Timestamped against the audit container, the drop lands in the same second the
container was stopped:

```
audit-1    2026-08-09T04:58:52.564Z INFO:     Shutting down
gateway-1  2026-08-09T04:58:52.917Z audit event 'auth_failed' dropped ...
```

That is `test_authentication_survives_the_audit_service_being_down` doing its
job, exactly as `CLAUDE.md` predicts. The verifier confirmed **zero drops inside
its own run window** (05:03:58–05:09:58), so the receipts step 9 points at are
complete.

### 5.6 Commands run, for reproduction

```bash
# session start
git mv SESSION_REPORT.md reports/session-4.md && git commit    # 27b8aa3

# change 1's risk, measured before anything was built
uv run scratchpad/ask.py dana "Which students seem to be struggling this term?"   # x3
uv run scratchpad/ask.py kim  "Which students seem to be struggling this term?"
uv run scratchpad/ask.py pat  "Which students seem to be struggling this term?"

# change 4
uv run scripts/seed.py
docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
uv run scratchpad/noor5.py 3 ; uv run scratchpad/noor5.py 5     # 5 of 8 refusal rows

# changes 2, 3, 5 land, then everything that reads them restarts
docker compose restart mcp-colleague mcp-canvas mcp-labor orchestrator ui-advisor ui-exec

# acceptance
uv run pytest tests/ -q                                          # 122 passed in 31.51s
docker compose logs --since 30m 2>&1 | grep "dropped"            # the disruptive test, §5.5
python3 -  # AST: both prompts single string constants
```

The services carry no `--reload`, so a code or prompt edit does nothing until
the container restarts. My first eight noor runs were made before the restart
and therefore against the previous prompt; everything the verifier measured was
after it. Worth knowing for the next session.

Scratchpad helpers live in
`/tmp/claude-1000/-home-todd-projects-harness-poc/e5cd5dd8-6a88-4667-85a6-4151b6fc5010/scratchpad/`
and are throwaway; nothing in the repository depends on them.

---

## 6. Deviations from the brief

1. **The program-code sentence has a conditional clause the brief did not
   specify.** `list_programs_catalog` is dean-only in `config/registry.yaml`,
   so an unqualified "call it first" is an instruction faculty cannot follow.
   The prohibition on guessing stays absolute. §2.2.
2. **Three `services/mcp-*/app.py` files changed, two lines each**, outside the
   brief's diff list. Classification by exception type requires the raise sites
   to raise that type; Session 4 made the identical amendment for mcp-kuali.
   §3.
3. **The two finding-4 tests are parametrized over three servers each, not four
   each.** Every server appears in at least one. Two of the eight cells do not
   exist — mcp-colleague has no reachable bad argument, mcp-labor refuses
   nobody — and the test file documents both rather than skipping them. §2.4.
4. **Three sentences of `SPEC.md` §5 changed, beyond §7's step 2.** Change 4
   made the spec's statement of who teaches what false, and `CLAUDE.md` says the
   spec wins on conflict. §2.5.
5. **One starter-button label changed** ("Struggling advisees" → "Who is
   struggling") so the button does not promise advisees for a question about
   students. §2.1.
6. **The verifier ran step 5b ten times, not five.** Its reasoning — five
   samples cannot separate 20% from 40% — is right, and the extra five are why
   the fabrication rate is a number rather than an anecdote.
7. **Nothing was fixed after the verifier ran.** Its findings 1–12 are all
   recorded and none is acted on, per "measure and report".

---

## 7. Open questions

1. **Step 5b fabricates BUS-201-A data in 3 of 10 runs.** This is the only
   step-level FAIL and the only genuinely new problem this session found. It is
   not fixable in `config/registry.yaml` — nothing there can force a tool call.
   Three routes, in my order of preference:
   a. **Re-cast the beat.** Ask noor about a section in a subject she does not
      teach at all — `HIM-210-A` — so there is nothing in her own list for the
      model to reason from and less for it to invent around. One line in
      `SPEC.md` §7.5 and one starter button. Cheapest, and it does not touch a
      prompt.
   b. **A prompt sentence** in the reply-shape block requiring the tool to be
      called before any statement about a named section. Barred this session.
   c. **A tool-shaped answer** — have `get_section_engagement` return "not
      yours" as data rather than as an exception for faculty. This is a design
      change and it weakens the demo's best moment; I would not.
   Route (a) does not remove the underlying behaviour, only the demo's exposure
   to it. Say which you want.

2. **Step 7's narration.** 445 of 631 words in the worst of three runs, 51 of
   237 in the best. The tallies are now exact, so what is left is purely the
   order. Session 4 offered three options and you took none; the evidence you
   asked for is in §4.4 and in `DEMO_VERIFICATION.md` §(B). Reword, flip
   `AGENT_THINKING`, keep iterating, or ship it.

3. **Step 8 regressed on grounding**, and it was closed once. The model claimed
   a skill is taught in no program after fetching four programs of six. Rule 5
   already forbids this in as many words. Same three options as question 2.

4. **The four small new findings** — the fabricated "Lightcast" source on step
   3b, `mcp-labor`'s dead `refuse()`, `SPEC.md:142`'s unproducible example id,
   step 6's "presumably". Each is one edit. None was touched.

5. **Nothing is committed.** Thirteen files plus this report are in the working
   tree; `27b8aa3`, the Session 4 report move, is the only commit. Say the word
   and I will commit.
