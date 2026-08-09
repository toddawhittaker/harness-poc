# Patches kept on purpose

`item2-marker-correction.patch` applies cleanly to commit `0e08b1c` and carries
five passing tests: it makes the groundedness guard rewrite a reply's citation
markers, instead of rejecting the reply, when exactly one MCP server ran and the
markers do not all name it. It was reverted in Session 11 not because it was
wrong but because of a coupling described in `docs/LESSONS.md` entry 5 — the
guard's rejection was also what drove the retry that made the model call the
tool that refuses, so correcting instead of rejecting cost demo moment 5b its
tool-layer refusal in three of ten runs. **That coupling is an artefact of this
POC's client-held chat history and single-shot retry; in a server-held-history
architecture it does not exist, so the MVP should take this patch rather than
inherit the reversion.**
