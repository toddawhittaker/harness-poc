# Patches kept on purpose

Two patches from Session 11, whose work was measured, certified against, and
then reverted by a pre-authorized fallback. They are tracked because the
reversion was a judgement about *this* demonstration, not a verdict on the code:
what killed the change here is an artefact of the POC's architecture, and the
MVP will not have it. `SESSION_REPORT.md` §4 and §6 are the full account;
`docs/LESSONS.md` entries 5, 9 and 12 are the short one.

**Check the base commit before applying.** These are not both against the same
tree, and neither applies to `main` as it stands.

| Patch | Applies to | What it is |
|---|---|---|
| `item2-marker-correction.patch` | **`0e08b1c`** (and `main` today) | The scoped grounding lift on its own: `grounding.py`, `app.py`, `viewer.html`, and five tests |
| `session-11-full.patch` | **`1b55ba5`** — the pre-session commit | Everything the experiment ran on: the above, plus the thinking-flag split and `AGENT_THINKING=true` |

Verify rather than assume — `git apply --check <patch>` on the named commit
returns silently, and on any other tree it will tell you which files have moved.

## `item2-marker-correction.patch`

Makes the groundedness guard **rewrite** a reply's citation markers instead of
**rejecting** the reply, in the one case where the request itself settles what
the marker should have been: exactly one MCP server ran, and the markers do not
all name it. The rewrite is audited as `answer_marker_corrected`; the reply is
otherwise untouched; with zero or two-plus servers nothing happens at all.

It worked. Across ten runs of one demo beat it fired seven times and corrected
every one correctly, and it closed a failure mode outright — zero declines in
ten runs, against one in three before it.

**Why it was reverted, and why that should not travel.** The guard's rejection
had been doing a second job nobody had written down. Rejecting a reply triggered
a corrective retry that told the model to *call a tool before writing anything*,
and that retry was what drove the tool call the server refuses — the refusal
demo moment 5b puts on screen. Correcting the marker instead of rejecting left
the model's first answer standing, and its first answer was drawn from a roster
it already held, so the boundary was never touched and no refusal was recorded.
That coupling exists because this POC hands the whole conversation back to the
client on every turn and allows exactly one regeneration. **An architecture that
holds conversation state server-side, and can re-drive a turn on its own terms,
does not have it.** Take the patch; do not inherit the reversion.

The five tests cover the wrong-server correction, a marker naming no server at
all, the two-server case unchanged in both directions, a reply with no markers
never being given one, and a correct reply passing untouched.

## `session-11-full.patch`

The complete experimental configuration as measured, against `1b55ba5`: the
marker correction plus the split of `AGENT_THINKING` into one flag per model and
the agent switched into extended-reasoning mode. Apply this one to reproduce the
measurements in `SESSION_REPORT.md` §5 exactly — the arithmetic result the
reasoning arm bought, and the refusal it cost.

Note that the flag split itself was *not* reverted: it is on `main` already, in
its own form, with both flags defaulting off. Only this patch's `AGENT_THINKING`
default and its comment wording differ from what shipped.
