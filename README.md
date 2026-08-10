# harness-poc

A working miniature of an institution-owned AI layer — a *harness* — that sits
above a university's real systems, answers questions in plain language for people
in different roles, and enforces the institution's access rules at every step.

It is a proof of concept, built in three days, and it exists to make one
architectural argument checkable rather than plausible: **the user's own identity
travels with every request, end to end, and authorization is checked
independently at multiple layers.** The AI never acts as an all-seeing service
account, and no model's judgment is ever the security boundary.

The full specification is [`SPEC.md`](SPEC.md). The production design this
miniature is drawn from is [`ARCHITECTURE.md`](ARCHITECTURE.md).

## What it proves

1. **Multiplexing.** Two visually distinct chat applications drive one
   always-live harness service. The surfaces hold no logic and no roles.
2. **Role-based access control, enforced in layers.** The same question asked by
   an advisor and by a dean returns role-appropriate answers; an adjunct is
   refused politely at the gate. Then the demonstration bypasses the gate
   entirely — `curl` straight at the orchestrator with a low-privilege token —
   and the request is *still* refused, by the tool server, on the caller's own
   token.
3. **Synthesis.** One question is answered by joining independent governed
   sources — a student record system, a learning management system, a curriculum
   catalogue and labour-market data — against a shared controlled vocabulary,
   with citations to each source.
4. **Receipts.** An audit viewer shows every request: who asked, in which role,
   which tools ran, what was refused.

## What is real and what is fake

This distinction is the whole point, so it is stated plainly rather than buried.

**Fake:** the people, the data, and the upstream systems. Five demo personas,
three hundred generated students, four mock institutional servers. Nobody in this
repository exists.

**Real:** every mechanism the architectural claim depends on. Tokens are
RS256-signed JSON Web Tokens, verified by signature, issuer, audience and expiry
independently at six services. Tools are reached over the Model Context Protocol
(MCP) with streamable HTTP transport. Authorization is decided inside the tool
servers, per request, against the caller's token — never upstream, never by the
model. Every decision is audited.

Anything that would invalidate the architectural claim if faked is not faked.

## Quick start

Requires Docker Compose v2, Python 3.12 and [uv](https://docs.astral.sh/uv/).
You need an API key for an OpenAI-compatible model endpoint; the defaults point
at DeepSeek.

```bash
cp .env.example .env          # then set DEEPSEEK_API_KEY
docker compose up --build
```

That is enough. The four seed databases are committed, so no seeding step is
needed for a first run.

**On Linux, set `HOST_UID`/`HOST_GID` to whoever owns the checkout.** The
containers write into the bind-mounted `./data` as
`${HOST_UID:-1000}:${HOST_GID:-1000}`, and identity-stub generates its signing
key there on first boot. If `id -u` is not 1000, set both in `.env` — otherwise
identity-stub dies with `PermissionError: '/data/jwt_private.pem'` and audit with
`unable to open database file`, and both restart in a loop. Deploying as root
means `HOST_UID=0` and `HOST_GID=0`. macOS and Windows map ownership themselves
and need nothing.

## Deploying to a server or LXC

Verified on a clean Ubuntu 24.04 container: ten images build in about thirty
seconds and all ten services come up healthy. Only two things are needed on the
host —

```bash
curl -fsSL https://get.docker.com | sh     # Docker Engine + the compose v2 plugin
apt-get install -y git
```

— then clone, write `.env`, and `docker compose up -d --build`. Four things bite
in practice, all of them found by actually doing it:

1. **`HOST_UID`/`HOST_GID` again, and this is the one that will get you.** A
   fresh clone into `/root` is owned by `root:root` while `.env.example` ships
   `HOST_UID=1000`. Every service then starts and two die on the bind mount. Set
   both to `0` when deploying as root.
2. **`--profile tunnel` needs a real `TUNNEL_TOKEN`.** With it empty, the other
   nine services are healthy and `cloudflared` restarts forever on
   *"`cloudflared tunnel run` requires the ID or name of the tunnel"*, which does
   not obviously mean "your token is blank". Compose cannot fail fast on this
   without also breaking the non-tunnel path, so it is a check to make by eye.
3. **Docker inside an unprivileged LXC does not work**, and the errors do not say
   why. With `security.nesting=true` alone, `docker run` fails on
   `open sysctl net.ipv4.ip_unprivileged_port_start … permission denied`; adding
   `lxc.apparmor.profile=unconfined` moves it to
   `Could not check if docker-default AppArmor profile was loaded`. What works is
   a privileged container:

   ```bash
   incus config set <name> security.privileged true
   incus config set <name> security.nesting true
   incus config set <name> security.syscalls.intercept.mknod true
   incus config set <name> security.syscalls.intercept.setxattr true
   ```

4. **If the LXC host also runs Docker, Docker silently blocks the container's
   network.** Docker sets the iptables `FORWARD` policy to `DROP`; incus and LXD
   accept their bridge in a separate nftables chain at the same netfilter hook,
   and a `DROP` there wins. The symptom is that `apt-get update` inside the
   container times out on every mirror while DNS resolves fine. Fix it in
   `DOCKER-USER`, which Docker will not overwrite:

   ```bash
   iptables -I DOCKER-USER -i incusbr0 -j ACCEPT
   iptables -I DOCKER-USER -o incusbr0 -j ACCEPT
   ```

   These do not survive a reboot on their own — persist them with
   `iptables-persistent` or a small systemd unit. Related: if the bridge hands
   out an IPv6 address the host cannot route, `apt` prefers IPv6 and stalls;
   `incus network set incusbr0 ipv6.address none` is the quickest cure.

Ports bind to `127.0.0.1` by design, so nothing is published off the box. Reach
the surfaces through the tunnel, or over an SSH port-forward for a local check.

| Surface | URL | What it is |
|---|---|---|
| Advisor Workspace | http://localhost:8080 | Chat application, warm theme |
| Executive Insights | http://localhost:8081 | Chat application, cool theme |
| Audit viewer | http://localhost:8030 | Every request, refusal and tool call, polling every two seconds |

Sign in to **either** application as any persona — access follows the token's
roles, not the application, and proving that is part of the demonstration. The
password is `demo` for all five.

| Persona | Name | Roles |
|---|---|---|
| `dana` | Dana Whitfield | advisor |
| `kim` | Kim Okafor | dean |
| `noor` | Noor Haddad | faculty (teaches two sections) |
| `pat` | Pat Reyes | adjunct — public data only |
| `sam` | Sam Lindqvist | advisor **and** dean |

### Seeing the receipts without running anything

The audit viewer starts empty, deliberately — in a live demonstration the room
should watch its own rows arrive. If you want to look at a real set first,
`data/audit-sample.db` is a frozen 105-row extract of the closing certification
run (audit ids 9770–9874), which
[`docs/DEMO_VERIFICATION.md`](docs/DEMO_VERIFICATION.md) documents beat by beat
with a row map. On a fresh clone:

```bash
cp data/audit-sample.db data/audit.db     # only before the first start
docker compose up --build
```

The viewer then opens on the certified pass: eleven answers, twelve
authentication failures from the probe matrix, one gate refusal, one skill
refusal, and the amber tool-layer refusals from the bypass and the faculty
boundary. The sample is never written to — the audit service writes
`data/audit.db`, which stays untracked.

To re-generate the fake data:

```bash
uv run scripts/seed.py
docker compose restart mcp-colleague mcp-canvas mcp-kuali mcp-labor
```

The restart is not optional. The servers hold the deleted database files open,
so without it you keep reading the old data.

`scripts/seed.py` is the source of truth for what is in those databases, and it
is deterministic (`random.seed(398)`). Because the generated databases are also
committed, the two can drift apart silently — so there is a check:

```bash
uv run scripts/verify_seed.py
```

It re-runs the seed into a temporary directory, never touching `data/`, and
compares every table by schema, row count and an order-independent digest of the
contents. Comparing the files byte for byte would be useless, because SQLite page
allocation is not stable across rebuilds and two databases holding identical rows
routinely differ as files.

## The demonstration

The fourteen-minute script is [`SPEC.md` §7](SPEC.md). The two beats worth
knowing about before you read it:

**The bypass** (`scripts/demo_bypass.sh`) mints an adjunct's token and calls the
orchestrator directly, skipping the gateway and its router — "suppose someone
sweet-talks or skips the AI gate." The tool server refuses anyway, and the
refusal lands amber on the audit page. One command, and it is deterministic
because a script makes the call rather than a model.

**The faculty/dean asymmetry.** A faculty member asks about a section she does
not teach and is refused by name; a dean asks the identical question and is
served. Same call, same argument hash, different token, decided inside the tool
server.

## How it fits together

The token is passed through at every hop, and every service validates it
independently rather than trusting the one before it.

```
  Chainlit app          gateway              orchestrator            MCP servers
  (:8080 / :8081)       (:8000)              (:8010)                 (:8021-8024)
        |                  |                      |                       |
        |  Bearer token    |    Bearer token      |     Bearer token      |
        +----------------->+--------------------->+---------------------->+
        |                  |                      |                       |
        |             verify_token           verify_token            verify_token
        |             router triage          registry filtering      ENFORCEMENT
        |             (not a judge)          (hides tools)           (decides)
        |                  |                      |                       |
        +------------------+----------------------+-----------------------+
                                     |
                                  audit (:8030)
```

**Authorization decisions live only in the MCP servers.** The gateway's router is
triage — it classifies the question and refuses the obviously out-of-scope
politely — and it fails *open* on a parse error, which is safe precisely because
it is not the enforcement layer. The orchestrator filters the tool registry so a
model never sees a tool its caller cannot use, but that is defence in depth, not
the boundary.

Services: `identity-stub` (:8001) stands in for an enterprise identity provider
and mints the RS256 tokens; `gateway` (:8000) is the front door; `orchestrator`
(:8010) is the always-live harness wrapping a Pydantic AI agent; `mcp-colleague`
(:8021), `mcp-labor` (:8022), `mcp-canvas` (:8023) and `mcp-kuali` (:8024) are
the four governed tool servers; `audit` (:8030) collects the receipts. All ports
bind to `127.0.0.1` only.

The orchestrator routes an extended-reasoning budget per `(intent, role)`: the
dean's synthesis questions get it, everything else does not. `docs/LESSONS.md`
entry 9 explains why, with the measurements.

## Tests

The negative-authorization suite is the mandatory one. It uses real tokens from
identity-stub — nothing is mocked, weakened or bypassed, in tests or anywhere
else.

```bash
docker compose up -d          # the stack must be running
uv run pytest tests/ -q       # 162 tests
```

It covers: a missing token rejected at all six token-validating services
independently; expired tokens, tampered signatures and wrong audiences rejected;
an adjunct's valid token refused at the tool layer; an advisor refused for a
student who is not theirs; and the faculty/dean asymmetry proven at the tool
server on an identical call.

## Where to read next

| File | What it holds |
|---|---|
| [`SPEC.md`](SPEC.md) | The build specification, including the demo script (§7) and the honest shortcuts (§11) |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The production design this is a miniature of |
| [`docs/DEMO_VERIFICATION.md`](docs/DEMO_VERIFICATION.md) | Every certification pass, newest first. The current one is Session 17 |
| [`docs/LESSONS.md`](docs/LESSONS.md) | Thirteen things the build taught us, each with the measurement behind it |
| [`reports/`](reports/) | Session-by-session build reports, Sessions 2 to 17, with the commands run and their output |

`docs/LESSONS.md` is the most portable part of this repository. It is what
seventeen sessions of measuring the same defects produced, and the strongest
finding in it is that changes making a bad outcome *impossible* held every time,
while changes *asking* a model not to produce one decayed, moved, or reappeared
in a new shape.

## Known honest shortcuts

Say these out loud rather than hiding them; `SPEC.md` §11 has the full list.
Token pass-through stands in for a proper on-behalf-of token exchange. Chat
history is held by the client, which keeps the harness stateless and is also the
structural cause of one defect class (`docs/LESSONS.md` entry 7). There are no
writes, no small-cell suppression, and no TLS between containers — the tunnel
terminates TLS.

## If you deploy this anywhere public

Two things matter, and neither is theoretical.

**Set real Chainlit cookie secrets.** `CHAINLIT_AUTH_SECRET_ADVISOR` and
`CHAINLIT_AUTH_SECRET_EXEC` fall back to defaults that are published in
`docker-compose.yml`. Those defaults are fine on localhost and nowhere else: a
public tunnel plus a known cookie secret is a forgeable login. They sign each
application's own session cookie and have no bearing on the harness tokens.

**`data/jwt_private.pem` is a real signing key and is not in this repository.**
identity-stub generates it on first boot if it is absent. Do not commit one:
publishing it would let anyone mint a valid token for any persona, which is
precisely the claim this POC exists to make.

The optional Cloudflare tunnel profile is `docker compose --profile tunnel up -d`,
with ingress documented in [`tunnel/config.yml`](tunnel/config.yml).

## Licence

MIT — see [`LICENSE`](LICENSE).
