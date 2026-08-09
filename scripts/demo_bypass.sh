#!/usr/bin/env bash
# The bypass (SPEC §7 step 4) — the money shot of the whole demo.
#
# The claim being tested: the AI gate is not what protects the data. So skip it.
# Take a real token belonging to someone with no data roles, go straight past
# the front door, and see how far it gets.
#
# It gets stopped twice, by two layers that have never heard of each other:
#
#   Layer 2, the orchestrator: pat's roles are mapped against config/registry.yaml
#            and the advisee tools are never put in the model's view. There is
#            nothing to sweet-talk it into calling.
#   Layer 3, mcp-colleague: skip the orchestrator as well and call the tool
#            server itself. It re-validates the token and refuses on the role.
#            This is the enforcement point. It would refuse even if every layer
#            above it were compromised, misconfigured, or absent.
#
# Nothing here is mocked. Real RS256 token, real services, real refusals.
#
# Usage: scripts/demo_bypass.sh
set -euo pipefail

IDENTITY_URL="${IDENTITY_URL:-http://localhost:8001}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8010}"
COLLEAGUE_URL="${COLLEAGUE_URL:-http://localhost:8021}"
AUDIT_URL="${AUDIT_URL:-http://localhost:8030}"

bold=$(tput bold 2>/dev/null || echo "")
dim=$(tput dim 2>/dev/null || echo "")
reset=$(tput sgr0 2>/dev/null || echo "")

step() { printf "\n%s==> %s%s\n" "$bold" "$1" "$reset"; }
show() { printf "%s%s%s\n" "$dim" "$1" "$reset"; }

# --------------------------------------------------------------------------
step "1. Mint a real token for pat (adjunct — no data roles)"
# --------------------------------------------------------------------------
show "POST $IDENTITY_URL/token"

TOKEN=$(curl -sf -X POST "$IDENTITY_URL/token" \
  -H 'content-type: application/json' \
  -d '{"persona":"pat","password":"demo"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

python3 - "$TOKEN" <<'PY'
import base64, json, sys
payload = sys.argv[1].split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
print(f"    signed RS256, sub={claims['sub']}  name={claims['name']}  roles={claims['roles']}")
PY
echo "    This token is valid. Every service below will verify it and accept it as pat."

# --------------------------------------------------------------------------
step "2. Skip the gate. Curl the orchestrator directly."
# --------------------------------------------------------------------------
show "POST $ORCHESTRATOR_URL/chat   (no gateway, no router, no UI)"

curl -sf -X POST "$ORCHESTRATOR_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"message":"List my advisees and their GPAs.","history":[]}' \
  | python3 -c '
import json, sys, textwrap
body = json.load(sys.stdin)
print("    tools the model actually called:", body.get("tools_used") or "none")
print()
for line in textwrap.wrap(body.get("reply", ""), 74):
    print("    " + line)
'
echo
echo "    Registry filtering: pat holds only the adjunct role, so the advisee"
echo "    tools were never placed in the model's view. Not refused — absent."

# --------------------------------------------------------------------------
step "3. Skip the orchestrator too. Call the tool server itself."
# --------------------------------------------------------------------------
show "POST $COLLEAGUE_URL/mcp   method=tools/call  name=get_my_advisees"

curl -sf -X POST "$COLLEAGUE_URL/mcp" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_my_advisees","arguments":{}}}' \
  | sed -n 's/^data: //p' \
  | python3 -c '
import json, sys
result = json.load(sys.stdin).get("result", {})
for block in result.get("content", []):
    print("    " + block.get("text", ""))
print("    isError:", result.get("isError"))
'
echo
echo "    That refusal came from mcp-colleague, which re-validated pat's token"
echo "    and checked the role itself. No layer above it was involved."

# --------------------------------------------------------------------------
step "4. Both attempts are on the record."
# --------------------------------------------------------------------------
show "GET $AUDIT_URL/events"

sleep 1
python3 - "$AUDIT_URL" <<'PY'
import json, sys, urllib.request

rows = json.load(urllib.request.urlopen(f"{sys.argv[1]}/events?limit=40", timeout=5))
mine = [row for row in rows if row.get("sub") == "pat"][:6]

print(f"    {'time':<10}{'service':<16}{'event':<17}{'decision':<10}detail")
print("    " + "-" * 72)
for row in reversed(mine):
    detail = row.get("detail", {})
    note = detail.get("tool") or detail.get("intent") or ""
    print(f"    {row['ts'][11:19]:<10}{row['service']:<16}{row['event']:<17}"
          f"{detail.get('decision', ''):<10}{note}")
PY
echo
echo "    The refused row shows amber in the audit viewer at $AUDIT_URL"
echo
printf "%sTwo layers, independently enforced, neither trusting the other.%s\n" "$bold" "$reset"
printf "%sThe model was never the security boundary.%s\n\n" "$bold" "$reset"
