# What the POC taught us

This is the transferable part of the harness proof-of-concept: the things we
learned building it that would cost the MVP team real time to learn again. It
is written for people who have not read the code. Each entry says what
happened, where the evidence is, and what to do about it in the production
system described in `ARCHITECTURE.md`.

The POC is a working miniature of that system: one always-live service (the
"harness") sitting above four mock institutional systems, reached by two thin
chat applications, with the user's own identity carried end to end and
authorization checked independently at every layer. The identities and the data
are fake. The mechanisms — signed tokens, per-request validation, tool-level
enforcement, the audit trail — are real, which is why the findings below
transfer.

Every claim here is drawn from the session reports in `reports/session-*.md`
and the verification records in `DEMO_VERIFICATION.md`. Session numbers are
given so the underlying evidence can be checked.

A note on how to read this. The single most useful pattern across thirteen
sessions is stated in entry 4: **defects we fixed in code stayed fixed, and
defects we fixed by rewriting instructions to the model came back.** Most of the
other entries are instances of it.

---

## 1. A per-request variable is not per-request when the session is stateful

**What happened.** The obvious way to hand a validated identity to a tool is to
put it in a context variable — a per-request slot the framework provides — set
by middleware when the request arrives, and read by the tool that runs a moment
later. In the Model Context Protocol server framework we used (FastMCP), in its
default stateful mode, this is wrong, and wrong in the direction that matters.
A stateful session runs every subsequent tool call inside the task created by
the *initialize* request. A context variable set on a later request is
invisible to the tool, so the tool keeps reading the identity of whoever opened
the session.

Concretely: open a session with user A's token, then call a tool with user B's
token, and the tool authorizes as A. One caller acting as another, silently,
with both tokens valid.

We did not infer this. A probe server opened a session with `Bearer FIRST` and
called a tool with `Bearer SECOND`; the tool read `FIRST` while the underlying
request scope showed `SECOND` correctly. The fix was to run the servers
stateless (`stateless_http=True`) and read the caller's claims from the
per-request scope rather than from any ambient variable.

**Where.** Session 2, §3.1. Regression tests in `tests/test_auth.py` assert the
observable behaviour — a session opened with one persona's token and driven
with another's returns the second persona's answer — so they keep holding
whichever mechanism is underneath.

**What the MVP should do.** Treat "where does the tool read the caller's
identity from?" as an explicit design decision with a written answer, not as a
convenience the framework provides. Prefer reading identity from the request
itself at the point of use. Whatever you choose, write the two-token probe as a
test before you need it: it is about thirty lines, it runs against the live
service, and it is the only thing that distinguishes a correct implementation
from one that looks correct.

---

## 2. An authorization refusal must not be framed to the model as "try again"

**What happened.** The agent framework's tool client had a default —
`tool_error_behavior='retry'` — that converts any tool error into a retry
instruction to the model: *that failed, correct yourself and try again.* For a
transient error that is sensible. For an authorization refusal it is exactly
wrong. The model is being told to work around a boundary the institution just
enforced, it burns the run's retry budget doing so, and when the budget runs
out the request fails with a server error instead of a polite refusal.

Setting the behaviour to `failed` shows the model the refusal as a *result* it
can read and relay. The demo beat where a faculty member is refused another
instructor's section then produces one tool call, one refusal, and one relayed
sentence.

**Where.** Session 2, §3.2.

**What the MVP should do.** Refusals and failures are different kinds of event
and must be plumbed differently from the tool layer up. A refusal is an answer:
it should reach the model as data, reach the user as prose, and reach the audit
log as a decision. Audit any framework default that decides what happens after
a tool returns an error — the defaults are written for flaky networks, not for
access control.

---

## 3. In a router prompt, describing what a role receives decides what it may ask

**What happened.** The gateway runs a small, fast model as a triage step: is
this question in scope, and is it plausible that a caller with these roles is
asking it? It is deliberately not the enforcement layer — enforcement lives in
the tool servers — but a refusal there means the request never reaches them.

We wrote two sentences into that prompt describing what deans receive
(aggregates, not individual student records). Neither sentence was a rule about
what deans may *ask*. Both were read as one. The dean persona was refused at
the gate on five of five attempts, deterministically, and the demo step where
two roles ask the same question and get role-appropriate answers simply
stopped working. Removing the first sentence did not fix it; the second leaked
the same signal.

What worked was to stop describing roles at all and state the rule as a closed
lookup: here is the list of role-to-category pairs, that list is the entire
test, do not narrow it by reasoning about how much of a category a role would
see in practice. Where holders had to be named, they were named positively and
as a closed list — "those two, and no third" — so that other roles are excluded
by omission rather than by a negation that reads like a verdict.

**Where.** Session 4, §4.1. The lesson in one line: *say who holds a thing,
never who does not.*

**What the MVP should do.** Keep triage prompts to a closed list with no prose
about roles, and test the routing decision for every role you support, not just
the one you changed. If a triage model can refuse, its refusals need the same
regression tests as the enforcement layer — and the reason enforcement lives
below it is precisely that this prompt is easy to get wrong.

---

## 4. Mechanical fixes held; prompt fixes regressed

**What happened.** This is the strongest pattern in the record. Ten sessions
produced two kinds of change: changes to the system that make a bad outcome
impossible, and changes to the model's instructions that ask it not to produce
one. The first kind closed defect classes permanently. The second kind bought
partial improvements that decayed, moved, or reappeared in a new shape.

The measured record:

| Defect | Fix | Result |
|---|---|---|
| Model invents another section's roster when refused (3 of 10 runs, Session 5) | Prompt paragraph forbidding invention | Reduced, not closed |
| Same defect | **Groundedness guard in code** (Session 6) | 0 of 10, and 0 in every session since |
| Reply claims a tool is unavailable that the caller holds | Prompt sentence, in the corrective instruction only (Session 7) | 8 of 10 |
| Same sentence promoted to the main prompt (Session 8) | Prompt | 5 of 5 — but introduced a new defect elsewhere (entry 8) |
| Receipt naming a tool that never ran | **Filtering the receipt against the offered set in code** (Session 9) | 10 of 10 clean, and provably so |
| Demo's opening tallies wrong (Sessions 5–7) | **Tool returns the counts it used to make the model derive** (Session 8) | The three tool-supplied counts correct in every run since |
| The one count the model still derived itself | Adding a fourth count field (Session 9) | Still wrong in 2 of 4 runs — the field was right, the sentence was not |
| Same count | **Changing the data so the four counts are four distinct facts** (Session 10) | See entry 9 |
| Students printed under the wrong group heading, with their real login gaps beside them (Session 11) | **Tool ships the group membership, not just the sizes** (Session 12) | 5 of 5 runs correct, and correct again in two certifications |
| The executive rollup's cross-program total: "78 missing submissions" where the six programs sum to 112 (Session 12) | **Tool returns the three totals it used to make the model add up** (Session 13) | 5 of 5 runs stated it verbatim, and the certification beat that had failed passed |
| A missing-to-enrollment ratio the model derived and stated wrong in both arms of one beat (Session 13) | **`missing_per_student` on every rollup row, computed from the two fields beside it** (Session 14) | All 30 ratios across 5 runs exact, and all 6 exact again in the closing certification |
| "0 of 5" for an occupation carrying 6 skills, a length the model counted itself (Session 13) | **`skill_count` on the occupation payload, taken from the list it ships with** (Session 14) | All 41 denominators across 5 runs exact, and all 4 exact again in the closing certification |

**Where.** Sessions 5 through 15; the table above is assembled from each
session's measurement section.

**Eight applications, eight holds, and no exceptions.** That is the whole of the
evidence for the advice below, and it is worth saying that each was chosen
because the last one worked: Session 12's certification failed one beat on a
derived total, named the fix in its own report, and Session 13 applied the same
technique one level out and the beat passed; Session 13's certification failed on
a ratio and a denominator, named both, and Session 14 shipped a field for each.
The rule is not "give the model good instructions about arithmetic". It is **put
the number in the payload.**

**And Session 14 found where the technique stops.** Both its fields worked
perfectly — every value either one states was transcribed correctly into every
reply, thirty ratios and forty-one denominators without a single error — and
*both beats failed their acceptance anyway*. Session 14's report states the
finding in the sentence this entry now ends on:

> Putting a number in the payload fixes the number, and moves the error to the
> next thing that is not in the payload.

The two things it moved to are now characterized, and the closing certification
scored them as a named tier rather than as surprises:

- **Ordinal claims about a field.** The tool ships six values; the *order* of
  those six is still the model's own work. Session 14 saw a wrong rank in 2 of 5
  runs while all six values printed correctly on the same screen, and Session
  15's certification saw three more instances — on a different beat from the one
  the field was aimed at, which is the part worth noticing.
- **Set-intersection counts across two servers.** How many of an occupation's
  skills appear in a programme's outcome tags. `skill_count` fixed the
  denominator because a denominator is a length. The numerator is a join, and no
  single tool result contains it.

**Neither was chased, and the reasons are different.** A rank *could* be a
payload field — a `rank` column, or rows returned in ranked order with the
docstring saying so — and the user declined it deliberately: the technique has
eight marks and needs no ninth, chasing each newly-exposed derived quantity is an
unbounded regress, and the residual is now a characterized, documented, low-cost
wart rather than an unknown. The intersection is different in kind. **A tool that
computed the tally would span two servers, and it would replace the synthesis the
demonstration exists to show with a lookup** — the whole claim of demo moments 7
and 8 is that the harness joins independent governed sources live, in the open,
against a shared controlled vocabulary. Building the join into a tool would make
the number reliable and the demonstration pointless. That boundary is a design
decision, and it is the one place in this record where "put the number in the
payload" is the wrong answer.

**What that means for the MVP.** The technique is close to free and it works
every time, so apply it to every count, total, ratio and length an answer will
state. Then expect the error to reappear one step out, and decide *there*
whether the next quantity belongs in the payload, belongs in a reasoning budget
(entry 9), or belongs left alone and written down. Not every derived number is
worth a field, and one of them — the one that is the product on display — must
not have one.

**What the MVP should do.** When a model misbehaves, ask first whether the
system can be arranged so the misbehaviour is impossible or is caught after the
fact by something deterministic. Give the model the number rather than the
ingredients; filter the output rather than requesting good output; check the
answer against what actually ran. Reserve prompt changes for things that are
genuinely about tone and shape, budget for measuring them across many runs, and
expect to re-measure whenever anything else changes. A prompt rule is a
probability, not a guarantee, and it should never be the only thing standing
between a user and a wrong answer.

### The final tally

The build ended after seventeen sessions. This is where the technique stands.

| | Count | Result |
|---|---|---|
| Payload fields shipped (Sessions 8–14) | **8** | **8 held.** No value any of them states has ever been wrong in any run afterwards |
| Prompt-only fixes aimed at the same defects | 4 | 0 held. Each bought a partial improvement that decayed, moved, or introduced a defect elsewhere |
| Reasoning budget, routed per intent (Sessions 16–17) | 1 | **Closed one residual class and not the other.** Entry 9 has the numbers |
| Certification passes with no wrong tool-stated figure anywhere | **2 of 2** since the eighth field shipped | Sessions 15 and 17 |
| Residual classes still open at the end | **3** | Ordinal claims; cross-server intersection numerators, now clean for twenty-five consecutive tallies under a reasoning budget; and prose generalisations over a group, named for the first time in Session 17 |

**The technique never failed and it never finished.** Eight for eight is the
strongest result in the record and it is also the reason the boundary matters:
each field closed a number and exposed the next thing that is not a number — a
rank, then a join, then a quantifier in a summary sentence. The last
certification's only defects were of exactly that shape. A team applying this
should expect the same shape of ending: the arithmetic goes quiet, and what is
left is the model's prose about arithmetic that is correct on the screen beside
it. Measure that, write down its rate, and tell the person presenting which
numbers are the tools' and which are the model's.

---

## 5. The groundedness guard: what it checks, what it cannot

**What happened.** After the fabrication described in entry 6, we added a check
in the orchestrator that runs after the model produces an answer and before the
user sees it. It compares the provenance the answer *claims* against what the
request actually did. The system already knew which tool belongs to which
server, so the check needed no new information:

1. If the answer carries a citation marker naming a server that made no call
   during this request, the answer is ungrounded.
2. If the answer carries no markers, made no tool calls, and states figures
   about students or sections, it is ungrounded — a number about people with
   nothing behind it is not a claim from anything.

On the first ungrounded verdict the orchestrator writes an audit row and
regenerates once, sending the problem as a trailing corrective message. That
message is never merged into the system prompt, so the cached prompt prefix
survives and the retry is cheap. If the second attempt is also ungrounded, the
user gets one flat sentence — "I can't ground an answer to that with the tools
available" — and that is audited too.

**The ledger.** Across Sessions 6 to 10 the guard fired roughly twenty times.
Every fire was a true positive. It has never rejected a good answer, and only
twice has a regeneration failed and the flat sentence reached a user.

**The two blind spots, both known and both deliberate.**

- *Prose that names a server without brackets.* The check looks for markers in
  square brackets. A reply saying "the tools I have can pull student records via
  the colleague server" names a server it never reached, in words, and passes
  untouched. Found in Session 6, §7.2; still open.
- *Replies with no citation marker at all.* An answer with no markers makes no
  false claim of provenance, so the first rule cannot fire, and if it does not
  state figures about people the second cannot either. Several otherwise correct
  answers have shipped with no citation. Session 7, §7.2; Session 9, §7.4.

A third thing it deliberately does not check: whether the marker on a given
sentence is the *right* one among the servers that did run. That is citation
accuracy, and a guard that guessed at it would start rewriting correct answers.

**We lifted that third restriction once, in the one case where it involves no
guessing, and the result is the most useful thing in this entry.** When exactly
one server ran, every fact in the reply came from that server, so a marker
naming a different one — or naming no server at all, like the `[cyb-bs
outcomes]` one run produced — is wrong in a way the request itself settles. We
made the guard rewrite those markers to the one server that answered, audit the
rewrite, and return the reply instead of rejecting it. It worked exactly as
designed: it fired seven times in ten runs of one demo beat, corrected every one
correctly, and it revealed that the model mislabels one source as another far
more often than anyone had realised — roughly twice in twelve requests.

**And we reverted it, because of a second-order effect nobody predicted.** The
guard's rejection had been doing a job nobody had written down. When it rejected
a reply, the corrective retry told the model to *call a tool before writing
anything* — and on the demo beat where a faculty member asks about a section she
does not teach, that retry is what drove the tool call that produced the
authorization refusal. Correcting the marker instead of rejecting the reply left
the model's first answer standing, and its first answer was to say "that is not
my section" from a roster it already had, without ever touching the boundary.
The answer was correct and the refusal never happened, so the audit trail had
nothing to show. The tool-layer refusal fell from a reliable event to about half
of ten runs.

**The lesson is about coupling, not about citations.** A guard that rejects work
has two effects: it stops the bad output, and it makes the system try again.
Anything downstream that depends on the retry is depending on the guard failing.
We had built a demonstration of a security boundary on top of a citation check's
willingness to reject, and could not see it until the check stopped rejecting.
Before you soften any check, ask what stops happening when it stops firing.
Entry 12 is the other half of that lesson: the demonstration should never have
depended on the retry in the first place.

The correction is kept, reverted but intact, as `docs/patches/item2-marker-correction.patch`
with its five tests. The coupling that killed it here comes from this POC's
client-held history and its single allowed regeneration; an architecture that
holds the conversation server-side, and can re-drive a turn on its own terms,
does not have it — so the MVP should take the patch rather than inherit our
reversion. `docs/patches/README.md` names the commit each patch applies to.

**Where.** Session 6, §2.1 (design and tests); Sessions 7–10 (the ledger).
`services/orchestrator/grounding.py`, about a hundred lines, no dependencies
beyond the standard library, tested against real transcripts of both good and
fabricated answers.

**What the MVP should do.** Build this early; it is small and it pays for
itself the first time it fires. Two design points transfer directly: check
provenance against execution rather than against the model's own account of
itself, and make the corrective retry a trailing message so the cached prefix
is not disturbed. Be explicit in the code about what the check does not cover —
ours says so in its own docstring, which is why the blind spots were found
deliberately rather than discovered on stage. If citations matter to your
users, add the "markers absent while tools ran" verdict we deferred.

---

## 6. Under refusal, a model may invent rather than stop — and the recovery is worth designing

**What happened.** The most serious finding of the build. In the demo beat where
a faculty member asks about a section she does not teach, the model would
sometimes see from an earlier tool result that the section was not hers, decline
to call the tool at all, and then invent the answer. In ten runs it happened
three times. One invented reply named twenty-four students in three tiers with
logins and missing-submission counts. The real section has three students. Not
one name or number matched.

This is invention rather than leakage — the better of the two bad outcomes,
because nothing was reached and nothing escaped — but it lands on the slide
whose entire point is that the boundary holds, and the audit page has no
refusal to show because no tool was ever called.

The rescue is worth describing because it is the mechanism working end to end.
In a later ten-run measurement, one run produced the same fabrication shape: an
answer citing the learning-management system having called nothing. The guard
rejected it, the regeneration called the tool, the tool refused, and what the
user saw was the refusal — with the amber row in the audit trail that the demo
needs. A fabrication was converted into the correct behaviour by a check in
code. That is run 10 of Session 6, audit rows 3398–3399.

**Where.** Session 5, §4.2 (the fabrication); Session 6, §4.1 (ten runs, zero
fabrications, and the rescue).

**What the MVP should do.** Assume that "I am not allowed to answer this" is a
state some model will fill with plausible text, and design for it: make the
refusal reachable as a tool result, check the answer's provenance before the
user sees it, and give the system one chance to retry against the real tool.
Note also what did *not* work — removing the near-identical section id that we
first blamed moved the rate from 5-in-8 to 7-in-10 and did not close it, and no
amount of registry configuration can force a tool call.

---

## 7. Client-held conversation history is the structural cause of invented lists

**What happened.** The chat applications hold the conversation and send it back
with each message, which keeps the harness stateless — a deliberate and, we
still think, correct choice for the POC. But what they hold is *rendered prose*,
not the tool results behind it. On the second turn of a conversation the model
therefore has its own earlier sentences and no data.

The failure that produced: a reply opened "My sections this term are CYB-310-A,
NET-131-D, and NET-425-A." Two of those three section identifiers exist in none
of the four databases. The first turn's tool call had returned the real list;
the second turn had only the first turn's prose, which mentioned one section.
The model needed a list nobody had asked it for and composed one. The guard
reported the answer as grounded, correctly by its own definition: the citation
named a server that had run. Right provenance, false content.

Two things helped. A prompt paragraph — any roster comes from a tool result in
the *current* turn, call the tool again if you need it — took the recurrence to
zero across five runs and then five more. And the underlying structure stayed
exactly as it was.

**Where.** Session 7, §7.1 and open question 1; Sessions 8 and 9, §4 (zero
recurrences).

**What the MVP should do.** Decide deliberately what a second turn can see. If
history stays on the client, treat every turn as if it has no data and make
re-fetching cheap and obvious. If you keep server-side conversation state, keep
the tool results in it, not only the rendered text — and note that this is a
real architectural fork with consequences for statelessness, cost and privacy,
not a detail. Either way, expect the failure to appear on multi-turn beats
first, because that is where the gap between what was said and what was
retrieved is widest.

---

## 8. "Tools used" must mean executed, and an attempt on a tool the caller lacks is its own event

**What happened.** The orchestrator reported `tools_used` on every answer and in
every audit row by reading the tool calls out of the model's run. That includes
calls to tools the caller was never offered — the registry filters the tool list
before the model sees it, so such a call reaches no server and returns nothing.

On the beat where a low-privilege user's request is sent straight to the
orchestrator to prove the layers below still refuse, the model asked for a tool
that user does not hold. Nothing was reached and nothing leaked. But the receipt
said `tools_used: ["get_my_sections"]` — a green audit row for a call that never
happened, on the slide whose entire subject is that the receipts are true. The
demonstration script printed the contradiction two lines apart.

The fix was to split the two ideas. What the model *asked for* is one list; what
*ran* is another. `tools_used` is now the executed list, so it is a subset of the
offered list by construction on every row. An attempt on an unoffered tool gets
its own audit row with a decision of `unoffered`, which no server row will ever
sit beside. The groundedness guard was also switched to judge against the
executed list, since a phantom call would otherwise put a server into the set
the guard believes answered.

Because ten runs of the beat produced no phantom call, we provoked one
deliberately to prove the new path fires live — three times, three rows, no
server contacted.

**Where.** Session 8, §7.1 (the defect); Session 9, §2.1 and §4.1 (the fix, ten
clean runs, and the deliberate probe).

**What the MVP should do.** Define every audit field as an observation of
something that happened, and derive it from the thing that happened rather than
from the model's account. "Asked for", "was allowed", and "ran" are three
different facts and all three are worth recording. When a fix's new path cannot
be triggered by normal traffic, provoke it on purpose and label the probe as a
probe — otherwise the fix is untested in production conditions.

---

## 9. Models get arithmetic wrong on the numbers they derive themselves

**What happened.** A defect class that outlived every prompt aimed at it. The
model reliably reports numbers a tool hands it and unreliably reports numbers it
computes from a list in front of it.

- Demo moment 1 opens with counts about an advisor's students. When the model
  counted them itself it said 23, then 24, then "eight" above a list of nine.
  Adding `advisee_count`, `flagged_count` and `quiet_count` to the tool result
  fixed all three, in every run since (Session 8).
- The next number in was the overlap — how many students are both flagged and
  inactive. We added that as a fourth field too. The field was correct and the
  sentence still was not: one run quoted the field and then overruled it on
  screen — *"The server reported 8 flagged-and-quiet, but the data shows 9"*
  (Session 9).
- On the skills-matching beat, coverage tallies were stated as "4 of 6" on a
  line that named three covered skills, and the error survived into the closing
  summary the room actually reads (Session 9).

**What thinking mode did to it.** In Session 10 we ran a controlled comparison
of the model's extended-reasoning mode ("thinking"), which the specification
disables by default for latency. Two arms, identical questions, fresh
conversations, five runs of each of the two arithmetic-heavy beats per arm.

| | Reasoning off | Reasoning on |
|---|---|---|
| Skills tallies: runs with a wrong tally | 2 of 5 | **0 of 5** |
| Advisor counts: runs stating a wrong count or arguing with themselves | 3 of 5 | **0 of 5** |
| Runs opening with visible deliberation before the answer | 5 of 5 | **0 of 5** |
| Median latency across all beats | 13.8s | 21.3s |

The mechanism is not mysterious. With reasoning disabled the model has nowhere
to work except the visible answer, so the scratch work is the answer and the
arithmetic errors are in it. With reasoning enabled the work happens before the
reply and the reply is shorter, cleaner and more accurate — at roughly a 50%
latency cost, and with one new failure of its own (entry 5's citation check
fired more often, and once declined).

**What reasoning mode cost, measured a session later.** We chose reasoning mode
on the table above and then ran the whole demonstration in it. The arithmetic
gain held — three runs of the counting beat and three of the tallies beat, no
wrong number in any of them. What we had not measured was the effect on
*behaviour*: a model that has already reasoned over a list it fetched a moment
ago tends to answer the next question from that list rather than call a tool
again. On the beat where a faculty member asks about a section she does not
teach, it answered "that is not my section" from the roster it already held and
never made the call the tool server would have refused — so the refusal, and the
audit record of it, stopped happening about half the time. We reverted to
non-thinking and certified in that configuration.

The final scoreboard, then, is a genuine trade rather than a winner. Reasoning
off: the counting beat put two students in the wrong group and contradicted
itself on screen, while every authorization refusal fired and was recorded.
Reasoning on: the arithmetic was clean and the refusal went missing.

**Where.** Sessions 5–9 for the defect class; Session 10 for the comparison;
Session 11 for the behavioural cost and the reversion; `DEMO_VERIFICATION.md`
for the per-run detail of both certification passes. The configuration that
produced the reasoning-on column is kept as `docs/patches/session-11-full.patch`,
so the comparison can be re-run rather than taken on trust.

**What the MVP should do.** Do not ask a model to do arithmetic that a tool can
do. Every count, percentage, and overlap that an answer states should be a field
in a tool result, computed from the rows being returned and defined once in code
so the tool and any test agree on what it means. Where the answer must place
things in groups, ship the group membership too — the identifiers, not just the
sizes — because a model given four correct counts will still sort by its own
notion of severity and let that ordering overwrite the definitions.

That last one is no longer advice. Session 12 built it: `get_my_advisees`
returns `flagged_ids`, `quiet_ids` and `flagged_and_quiet_ids` beside the four
counts, each count being the length of the list next to it, and the docstring
says the lists are authoritative. Five runs of the counting beat afterwards put
every student in the right group, with no reply contradicting itself — against
Session 11's certified pass, which had the counts right and two students under
the wrong headings with their real login gaps printed beside them. It is the
fifth instance of "let the tool compute it", and like the four before it, it
held.

The sixth followed immediately, on the same principle one level out. Session
12's certification pass printed six correct per-program missing-submission
counts and then closed on "78 missing submissions" for a catalog whose six rows
sum to 112 — the running total of the first four rows of its own table, stopped
after four. Session 13 had the rollup tool return `total_sections`,
`total_enrollment` and `total_missing_submissions` computed from exactly the
rows it ships, with the docstring saying the totals are authoritative and must
never be re-derived. Five runs afterwards stated the total verbatim, and so did
the certification beat that had failed. The two numbers that were still wrong in
that final pass were a ratio the model compared across programmes and the length
of a skill list it counted itself — neither of which any tool states, which is
the same sentence as the fix.

Where a derived number is unavoidable, budget for reasoning mode on that path
and measure it — but measure more than accuracy and latency. Reasoning mode
changes how eagerly a model calls tools, and if anything you care about depends
on a call actually being made, that is the thing to put on the scoreboard. This
is a per-workload decision, not a global setting, and the flag should be per
model rather than one switch for the whole system: ours governed the router and
the agent together until we separated them, which is one recreation of the wrong
container away from measuring one configuration and shipping another.

### The final scoreboard for this defect class

The build ended with the class narrowed rather than closed, and the shape of what
is left is the useful part. Three things were tried against it.

**Payload fields closed everything a tool can state.** Eight fields across
Sessions 8 to 14 — four advisee counts, three group-membership lists, three
rollup totals, a per-student ratio and a skill count — and every one held on
every run afterwards. Entry 4 has the tally. Session 15's closing certification
is the cleanest statement of the result: across twelve replies, **every figure a
tool result or the database states was exact** — every headcount, total,
denominator, growth percentage, wage, GPA, login percentage, missing count, seat
count, term, grade and credit count. That had never happened before in a
certification pass.

**Reasoning mode closed most of what payload fields cannot reach, and cost a
demonstration.** Session 10's controlled A/B, five runs of each arithmetic-heavy
beat per arm:

| | Reasoning off | Reasoning on |
|---|---|---|
| Skills tallies: runs with a wrong tally | 2 of 5 | **0 of 5** |
| Advisor counts: runs stating a wrong count or arguing with themselves | 3 of 5 | **0 of 5** |
| Runs opening with visible deliberation before the answer | 5 of 5 | **0 of 5** |
| Median latency | 13.8s | 21.3s |

Session 11 then ran the whole demonstration in it and found the bill: the
authorization refusal that demo moment 5 turns on stopped reaching the tool
server in about half of ten runs, because a model that has already reasoned over
a list it fetched answers from that list instead of calling again. We reverted.
The trade is genuine and it is not a winner either way.

**What remains in the shipping configuration, and at what rates.** Two classes,
both measured, both now written into `DEMO_VERIFICATION.md`'s rubric as a named
tier rather than treated as defects to be surprised by:

| Residual | Measured rate | Where |
|---|---|---|
| Ordinal claims about a tool-stated value — "second-highest", "the lowest" | wrong in **2 of 5** step-2 runs (Session 14); 3 further instances in Session 15's single-run certification, on a different beat | Any reply comparing values across rows |
| Cross-server intersection numerators — the "n" in "n of N" | wrong in **3 of 5** step-7 runs (Session 14); 0 of 1 in Session 15's certification | The qualification and gap syntheses |

Session 15's zero-error draw on both is one run per beat and is fully consistent
with those rates being unchanged; it is characterization, not improvement.

**The lesson, stated once.** A model gets right what it is handed and gets wrong
what it works out. Hand it everything a tool can compute — that is close to free
and it never failed once in eight applications. For what is left, you have three
honest options and you should choose deliberately rather than by default: put it
in the payload if a tool can own it; spend a reasoning budget on that path if the
number matters more than the latency and nothing downstream depends on the model
staying eager to call tools; or measure the rate, write it down, and tell the
person standing in front of the room which numbers on the screen are the tools'
and which are the model's. **The last option is not a failure. An unmeasured
residual is the failure.**

### Session 16: the second option, built and measured — and it bought one class, not both

The middle option above stayed advice for five sessions because the only switch
available was global, and Session 11 had shown what a global switch costs. So
Session 16 built the per-workload version this entry recommends: the gateway's
router assigns a reasoning budget per question from a table, and the orchestrator
spends what it is given. `agent_model(reasoning: bool | None)` takes the override,
the flag rides to the orchestrator beside the message, and every `answer_returned`
row states which budget answered.

**The routing worked, and the two things people expect it to break did not
break.** Across 33 requests and 66 model calls: every row carried the budget its
intent and role called for, **zero calls hit a cold prompt cache** (minimum 896
hit tokens, so per-request `thinking` settings do not disturb DeepSeek's prefix
cache), and the beat that a global reasoning flag destroys was untouched. Demo
moment 5's second turn reached the tool server and relayed the spec-fixed refusal
in **5 of 5 runs**, against roughly half of ten under Session 11's global flag —
because that beat was routed cheap on purpose. Both of Session 11's costs were
avoidable and the mechanism for avoiding them is a table.

**What it bought, and what it did not.** Reasoning went to the two synthesis
beats. Measured against the same beats in Session 14 without it:

| Residual | Session 14, no reasoning | Session 16, reasoning on that beat |
|---|---|---|
| Cross-server intersection numerators (step 7) | wrong in **3 of 5** runs | **0 of 5** — 40+ tallies, every one exact |
| Ordinal claims about a tool-stated value (step 2) | wrong in **2 of 5** runs | **1 of 5** — "the best rate on that one measure" about the second-best |

The intersection class went to zero and stayed there: five runs, every numerator
consistent with its own covered list, every denominator equal to `skill_count`.
The ordinal class did not. One run in five still misread a ranking of six values
it had printed correctly in the same reply, which is what four sessions of
prompt-shaped fixes also achieved. A second run in the same five stated one
programme's enrolment and missing count as another's — a wrong *tool-stated*
figure, which reasoning is not supposed to leave on the table at all.

**The experiment failed its acceptance, the pre-authorized fallback reverted it,
and it was then merged anyway on an explicit ruling** — that step 7 going to zero
and moment 5 going to 5 of 5 outweigh an ordinal rate that five runs cannot
distinguish from unchanged. Both halves of that are worth recording, because the
process and the decision are separate things: the criterion was written before
the measurement so the call could not be made by whoever was looking at the
result, and it was then made deliberately, in the open, by someone who had read
what failed. **The POC therefore ships with the router assigning reasoning
budgets per intent — the architecture document's model-pool design, implemented —
on a configuration no certification pass describes.** `DEMO_VERIFICATION.md` says
so at the top of its current certificate.

One design property that made the merge defensible and is worth copying: **only a
dean can draw a reasoning budget in the shipped table.** There is no `True` cell
for any advisor, faculty or adjunct pair, so the beats that depend on the model
staying eager to call tools cannot be routed expensive by a misclassification.
The protection is structural rather than a bet on the router picking the right
category.

**What the MVP should take from this.** Route the budget per intent — it is a
small table, it costs nothing to read, and it makes the Session 11 trade
disappear as a trade. Expect it to close set-intersection arithmetic and expect
it *not* to close ordinal claims: a rank is not arithmetic, and thinking longer
about six values does not make a model reliably order them. Ranks belong in the
payload or in the presenter's patter. And note the shape of the key: Session 16
had to route on `(intent, role)` because a four-category router cannot tell
kim's programme question from dana's advisee question, or noor's section question
from kim's rollup. **That is a taxonomy defect, not a design.** An MVP splits the
intents — `section_engagement` from `program_rollup`, curriculum synthesis from a
labour-market lookup — and budgets by intent alone, with no role in the table.

### Session 17: the routed configuration was certified, and this is how it ended

**The routing shipped, and Session 17 certified it.** Session 16 merged the
experiment on a ruling but left it described by no certification pass; Session 17
ran one full demo-verifier pass on the routed configuration — twelve scored
beats, no re-runs — and it passed twelve of twelve on tier (a), with the
reasoning budget correct on all eleven `answer_returned` rows. It is the second
consecutive certification in which no figure a tool or the database states was
wrong anywhere, and the first on the configuration that actually runs.

**What each residual class did under the routing, measured across twenty-one
replies and ten dedicated runs.** *Cross-server intersection numerators*: closed
in practice — 0 of 5 in Session 16, then 0 of 8 in the qualification beat and 0
of 12 in the gap beat, twenty-five consecutive correct numerators against Session
14's 3-in-5 wrong without reasoning. *Ordinal claims*: not closed, but the best
stretch in the record — 0 of 5 in a dedicated five-run measurement of the beat
where Session 14 measured 2 in 5 and Session 16 measured 1 in 5, and the full
six-programme ranking correct on the rollup beat that Session 15 got wrong twice.
One ordinal residual remained, on the plain-language beat. *Tool-stated value
integrity*: clean — Session 16's single cross-attachment, one programme's
enrolment stated as another's, did not recur in five runs of the same beat in the
same mode. *And a third class appeared*, which is Session 14's prediction coming
true a fourth time: a prose generalisation over a group, false for one member,
with every member's values printed correctly in the same reply.

**The kill-criterion was corrected before the measurement, and the correction is
part of the lesson.** Session 16's criterion had been *zero* ordinal claims, and
by Session 17 it was clear that no configuration in sixteen sessions had ever met
it, that three separate remedies had failed against that class, and that 1-in-5
against a 2-in-5 baseline is not distinguishable in five draws — so ordinals were
reclassified as a characterised tier-(b) residual and the criterion was moved to
the thing the routing genuinely put at risk, tool-stated value integrity. **The
correction was declared in writing before any run, which is the only reason it is
a criterion and not a rationalisation** — the same discipline that made Session
16's failure a real failure rather than a matter of taste.

**The POC therefore ends with the router assigning a reasoning budget per task —
`ARCHITECTURE.md`'s model-pool design, implemented, measured and certified.** The
last certificate in `DEMO_VERIFICATION.md` describes a system in which a triage
model decides what each question is worth before an execution model answers it,
the expensive budget reaches only the beats that were shown to need it, and every
receipt states which budget answered. That is not the whole of the model-pool
argument — there is one execution model here, not a pool — but the mechanism the
argument turns on is the table, and the table is the part that shipped.

---

## 10. Seed data is casting, and invariants beat aesthetics

**What happened.** The demonstration data is generated by one deterministic
script, and every fact a demo beat depends on is asserted in that script rather
than hoped for. The assertions are specific: this advisor has exactly 25
students of whom 9 carry flags; this student has exactly three open courses next
term and exactly one blocked by a prerequisite; this instructor holds no section
whose identifier resembles the one she will be refused for; these three skills
are taught by no program in the catalog, exactly, in both directions.

The discipline paid for itself repeatedly, and always at the moment when
something looked cosmetically wrong:

- A proposal to raise one program's average grade to a rounder number would have
  lifted a student above the flag threshold and changed the advisor's headline
  count. We kept the ugly number and the correct count (Session 8).
- A proposal to add a named skill to a course to thicken one partial match would
  have moved a different tally the same brief required to hold still, because the
  skill belonged to both occupations. We added a different skill and asserted its
  overlap profile so the choice cannot silently rot (Session 9).
- One student is deliberately near the end of his programme, so his honest answer
  is "nothing new to take". The script asserts he still has zero options, so
  nobody can quietly retune him into a better slide (Sessions 2 onward).
- In Session 10 we broke a nesting that had made two of the demo's four counts
  the same number about the same people, and the change had to hold every one of
  the twenty-odd other assertions. It did, first run.

The one aesthetic thing that mattered: a spread. For three sessions the six
programmes were within a tenth of a grade point and a few percentage points of
each other, so the executive answer had nothing to lead with until it reached a
second data source. Giving each programme its own profile — and asserting a
minimum spread — gave that beat a headline.

**Where.** `scripts/seed.py`, function `verify()`; Sessions 3, 8, 9 and 10.

**What the MVP should do.** For demonstration and test environments, write the
generator and the guard together, count things with the same function that wrote
them, and let the guard fail the build loudly. When a figure looks wrong,
establish which invariant it protects before you change it. And keep a written
casting table — who the demo asks about and why — beside the data, so the next
person changing a number can see what they are about to break.

---

## 11. Prompt-cache discipline is a rule you can verify from the audit trail

**What happened.** The model provider bills a cached prompt prefix at a small
fraction of an uncached one, and caching works by exact prefix match. So the
rule is: system prompts are fixed strings, tool schemas are registered in a
fixed order, and everything dynamic — the user's name, roles, question, history
— goes in messages *after* the prefix. No formatted strings in a system prompt,
ever.

We made this checkable rather than aspirational. Every model call's cache hit
and miss token counts go into the audit trail, and every session's acceptance
criteria include "zero calls with zero cache hits". In Session 10's comparison,
88 model calls across both arms reported a minimum of 896 hit tokens and not one
zero-hit call. Twice during the build, a proposed change was rejected because it
would have put dynamic content into a prefix; once, a corrective instruction was
deliberately implemented as a trailing message for the same reason.

**Where.** `SPEC.md` §1; `libs/harness_models/factory.py`; the standing cache
check in every session report.

**What the MVP should do.** Put the cache counters in the audit record from the
first day and make a zero-hit call a build failure, not a footnote. Also read
the right counters: our provider's total prompt-token count includes text it
prepends server-side, so reasoning about cache behaviour from the total sends
you hunting a bug that is not there. The hit and miss counters describe the
cache; the totals do not.

---

## 12. An enforcement receipt must never depend on the model volunteering to hit the boundary

**What happened.** The demonstration beat that proves the access rules hold has
a faculty member ask about a section she does not teach. The tool server refuses
her, the refusal is relayed to the screen, and an amber row appears in the audit
log — that row is the receipt, and it is the whole point of the beat. It only
ever appears if the model chooses to call the tool that will refuse it. Twice in
this build the model instead answered correctly from a list it already had —
"that is not one of your sections" — and the boundary was never touched, so
there was nothing to record. The answer was right and the proof was missing.
Nothing in the system made the call certain, and no amount of prompt wording
would have; a model that already knows the answer has no reason to ask. The
lesson is that a receipt is evidence about the enforcement layer, and evidence
about the enforcement layer must be produced by something that always runs. When
proof of refusal matters — for an audit, a compliance review, or a room full of
people being asked to believe you — generate it deterministically rather than
hoping the model walks into the wall. Our own demonstration already contains the
correct pattern and we did not notice: the bypass script (`scripts/demo_bypass.sh`)
calls the tool server directly with a low-privilege token, every time, and its
refusal row is the one receipt in the whole script that cannot fail to appear.

**Where.** Session 11, both certification passes; `reports/session-11.md` §9,
question 2.

**What the MVP should do.** Separate the two things the demonstration was
conflating. Conversational answers are best-effort and shaped by what the model
already knows. Proof that the boundary holds is a *test*, and it should be
produced by a scheduled deterministic probe — a small set of calls, made with
real tokens as real people, that are expected to be refused — writing its
refusals into the same audit log the conversations write into. Then the receipt
exists whether or not anyone asked the right question that day, and the audit
trail can answer "did the rules hold this week" without depending on a model's
choices at all.

---

## 13. Skills: behaviour is configuration, and configuration must be governed

**What happened.** In the last session we added the smallest possible version of
a feature the MVP will certainly want: a named block of instructions a user can
switch on, which changes how an answer is written without changing what it may
contain. One skill, `plain_language` — short sentences, everyday words, and an
explicit carve-out saying that figures, citations and refusals are untouched.

The interesting part is not the skill. It is that a skill is a piece of
behaviour arriving from outside the code, and everything we already knew about
governing *tools* turned out to apply unchanged to governing *behaviour*. Four
properties, and each one is a deliberate contrast with pasting extra text into a
prompt:

- **It exists in a registry.** `config/skills.yaml` is the whole catalogue. A
  caller sends a *name*; the instructions never travel on the wire. So a caller
  can ask for a skill and cannot author one, and an unknown name is refused
  rather than quietly ignored — an answer written in a register nobody chose,
  with nothing in the reply to say so, is the outcome worth avoiding.
- **It is role-gated, against the caller's own token.** Each skill names the
  roles that may activate it, checked in the same service, against the same
  verified claims, as the tool allowlist. A caller whose roles do not cover a
  skill is refused, courteously, and the refusal is audited.
- **It is injected as a trailing message.** The instructions go after the static
  system prefix and immediately before the question — never merged into the
  prefix. The prefix is what the provider caches (entry 11), and a skill that
  rewrote it would turn every request in the session into a cache miss. Across
  every arm we measured, the minimum cache hit stayed at its usual floor and no
  call reported zero hits.
- **It is visible afterwards.** `answer_returned` carries `active_skills`, so a
  reply's register is as recoverable from the audit trail as the tools behind
  it. Someone asking "why did this answer read differently?" gets an answer from
  the record rather than from memory.

None of this is authorization. A skill cannot widen what anyone may see, because
that decision lives in the tool servers, which know nothing about this file. The
only boundary the skill machinery enforces is the boundary on the skill itself.

**And it is not free.** With the skill switched on, the model became measurably
readier to answer before calling a tool. On the beat where a faculty member asks
about a section she does not teach, the tool-layer refusal appeared in 3 of 5
runs with the skill on against 4 of 4 with it off, the answer-provenance check
fired six times in ten replies against twice in eight, and one run ended in the
flat "I cannot ground an answer to that" sentence. This is entry 12's finding
arriving from a new direction: an instruction block sitting immediately before
the question competes with the question for the model's attention, and what it
displaces first is the decision to go and fetch something. So a behavioural
skill is a change to the agent loop, not a change to the stylesheet, and it
needs measuring on the beats that depend on a tool call actually being made —
not only on the beats whose prose it was meant to improve.

**What we did with that measurement is the part worth copying.** The session
that found it wrote the constraint into the demonstration script: *do not run
this skill on that beat.* That is a sentence in a document, and a document does
not stop anybody. The next session deleted one role from one line of the
registry — the skill is now granted to advisors, deans and adjuncts, and not to
faculty — and since the only faculty persona is the one whose beat was
measurably damaged, the dangerous combination stopped being reachable. A caller
who asks for it now gets a courteous refusal and an amber row instead of a
degraded answer.

The general form: **a measured behavioural risk should end up in the same
registry that governs everything else, not in a footnote about how to run the
demo.** The registry entry is testable, and a test now fails if anyone grants
the role back. The footnote was not, and nothing would have failed. Note also
what this did *not* require: no code changed, no prompt changed, and the two
chat applications were not touched — they hold no roles by design, so hiding the
switch per role would have put an entitlement decision in a surface, which is
precisely the thing this architecture refuses to do. The switch may still be
visible to a caller who cannot use it. The refusal is the enforcement.

**One thing we suspected and could not confirm.** The session that built the
skill saw a single reply sign the learning-management system's figures with the
student-record system's marker, and wondered whether writing in a plainer
register costs citation accuracy. Ten runs of the same question, five with the
skill on and five with it off, scored on whether every marker named the server
whose tool supplied that figure: **the distributions were identical** — two
replies in five correct on both sources, two in five signing both sources'
figures with one marker, one carrying a single source's figures correctly. The
skill neither improved nor degraded attribution. The one observation worth
keeping is the rate itself: on a question joining two systems, two answers in
five got the provenance wrong regardless of register, which is entry 5's third
blind spot measured rather than assumed. If citation accuracy matters to your
users, that is the number to design against, and no amount of style
configuration will move it.

**The activation taxonomy, which is the part worth stealing.** Every skill has
to answer one question before anything else: *whose judgement puts this on?*
Four answers, and each one encodes a different kind of thing.

| Activation | Whose judgement | What the skill encodes | POC-grounded example |
|---|---|---|---|
| `user` | the person asking | a **choice** | `plain_language` — a dean decides she wants this answer in plain words. Nobody else is involved, and it is off again next session |
| `role-default` | the institution | a **policy** | a skill that is on for every adjunct, requiring each answer to say which figures are public data and which are not. The adjunct did not choose it and cannot switch it off |
| `surface-default` | the product | a **genre** | the Advisor Workspace and Executive Insights are two rooms. "One student at a time, next action first" belongs to the first; "programme-level headline first, no individuals" belongs to the second. The door decides what kind of document this is |
| `model-invoked` | the model | **know-how** | the skills-matching procedure — fetch the programme's outcomes, intersect the skill tags as exact strings, report what is covered and name what is missing. Today it sits in the static prompt and is paid for on every request, including the ones that will never need it |

**One hard rule, and it is a rule rather than a preference: a policy skill is
never model-invoked.** If the institution decided it, the model does not get a
vote on whether it applies. The moment a compliance framing, a suppression rule,
or a required disclosure becomes something a model loads when it judges the
situation calls for it, the institution's policy has become the model's opinion
— and the whole argument of this system is that the model is never the boundary.

Model-invoked skills are still legitimate, for know-how, under two conditions
that make them safe: they are **catalog-governed** — the model chooses *when*,
the registry governs *what exists*, and a skill the registry does not contain
cannot be summoned — and they are **audit-stamped**, so the record says which
skill loaded on which request. The model picks the moment; it never picks the
menu, and it never picks in secret.

**Where.** Session 12 built it; Session 13 scoped it by registry and measured
the attribution question. `config/skills.yaml`,
`services/orchestrator/skills.py` (about a hundred and thirty lines, no
dependency beyond the YAML parser already present), `tests/test_skills.py`.

**What the MVP should do.** Build the registry before the second skill, not
after: two skills pasted into a prompt look cheaper than one registry right up
to the moment somebody asks which users have which behaviours switched on. Put
`activation` in the schema from the first day even if only one value is
implemented, because it is the field that stops a policy from being written as a
preference. Gate skills on roles in the same place and against the same claims
you gate tools, so there is one answer to "where are entitlements decided" and
not two. And ship the kill switch with the feature: ours is one environment
variable that removes the toggle from both surfaces, stops the field being sent,
stops it being validated, and leaves no trace in the audit trail — which is what
let us certify the feature and the absence of the feature in the same session.
Then, when a skill turns out to hurt something, move the constraint into the
registry rather than into the runbook: a role removed from a line is enforced
and testable, and a sentence telling people not to do it is neither.

---

## What the POC did not prove

Stated plainly, because these are the questions the MVP has to answer and we did
not:

- Writes. Everything here is read-only. Authorization for a write, and the audit
  and reversal story around it, is untouched ground.
- Real identity. The POC mints its own signed tokens and passes them through
  every hop. Production swaps that for the institution's identity provider and a
  proper on-behalf-of exchange. The enforcement code does not change; the token
  issuance does.
- Scale. Tool clients are constructed per request, everything is SQLite, and no
  component has been under load.
- Small-cell suppression. A dean's aggregate over three students is currently an
  aggregate over three students.
- Anything about accuracy at the volume a real catalogue implies. Our data is
  300 students and 12 occupations, tuned so the joins are provable by eye.
