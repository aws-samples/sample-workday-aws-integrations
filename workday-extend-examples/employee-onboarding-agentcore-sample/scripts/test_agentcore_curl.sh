#!/bin/bash
# AgentCore OAuth Test Script
# Demonstrates how to call the AgentCore runtime with curl using values from .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
CONFIG_FILE="$REPO_ROOT/.bedrock_agentcore.yaml"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ .env file not found at $ENV_FILE. Run 'make deploy' (or scripts/deploy.sh) first."
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ .bedrock_agentcore.yaml file not found at $CONFIG_FILE. Run 'make deploy' first."
    exit 1
fi

# Load environment variables from .env without polluting parent shell
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${RUNTIME_CLIENT_ID:?RUNTIME_CLIENT_ID not set in .env}"
: "${RUNTIME_CLIENT_SECRET:?RUNTIME_CLIENT_SECRET not set in .env}"
: "${RUNTIME_TOKEN_ENDPOINT:?RUNTIME_TOKEN_ENDPOINT not set in .env}"
: "${RUNTIME_SCOPE:?RUNTIME_SCOPE not set in .env}"

echo "🔐 Getting OAuth2 access token..."

BASIC_AUTH=$(python3 - <<'PY'
import base64, os
cid = os.environ["RUNTIME_CLIENT_ID"]
secret = os.environ["RUNTIME_CLIENT_SECRET"]
print(base64.b64encode(f"{cid}:{secret}".encode()).decode())
PY
)

TOKEN_RESPONSE=$(curl -sS -X POST "$RUNTIME_TOKEN_ENDPOINT" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H "Authorization: Basic $BASIC_AUTH" \
  -d "grant_type=client_credentials&scope=$RUNTIME_SCOPE") || {
    echo "❌ Failed to contact token endpoint."
    exit 1
  }

ACCESS_TOKEN=$(TOKEN_RESPONSE="$TOKEN_RESPONSE" python3 - <<'PY'
import json, os
data = json.loads(os.environ["TOKEN_RESPONSE"])
print(data.get("access_token", ""))
PY
)

if [[ -z "$ACCESS_TOKEN" ]]; then
    echo "❌ Access token missing. Full response:"
    echo "$TOKEN_RESPONSE"
    exit 1
fi
echo "✅ Access token obtained"

# Read runtime ARN and region from .bedrock_agentcore.yaml
RUNTIME_JSON=$(CONFIG_FILE="$CONFIG_FILE" python3 - <<'PY'
import os, yaml, json
with open(os.environ["CONFIG_FILE"], "r", encoding="utf-8") as fh:
    cfg = yaml.safe_load(fh)
default_agent = cfg["default_agent"]
agent_cfg = cfg["agents"][default_agent]
arn = agent_cfg["bedrock_agentcore"]["agent_arn"]
region = agent_cfg["aws"].get("region") or "us-east-1"
print(json.dumps({"arn": arn, "region": region}))
PY
) || {
    echo "❌ Failed to read .bedrock_agentcore.yaml."
    exit 1
}

export RUNTIME_JSON
REGION=$(python3 - <<'PY'
import json, os
data = json.loads(os.environ["RUNTIME_JSON"])
print(data["region"])
PY
)
ENCODED_ARN=$(python3 - <<'PY'
from urllib.parse import quote
import os, json
data = json.loads(os.environ["RUNTIME_JSON"])
print(quote(data["arn"], safe=""))
PY
)

MESSAGE="${1:-onboard jane doe as product manager}"
echo "🤖 Invoking agent with message: '$MESSAGE'"

INVOCATION_URL="https://bedrock-agentcore.${REGION}.amazonaws.com/runtimes/${ENCODED_ARN}/invocations?qualifier=DEFAULT"

# AgentCore runtime streams SSE. Capture the raw body, then let Python
# concatenate the `text` fields from each `data: {...}` line into a single
# readable transcript.
REQUEST_BODY=$(MESSAGE="$MESSAGE" python3 -c 'import json, os; print(json.dumps({"message": os.environ["MESSAGE"]}))')

RAW_RESPONSE=$(curl -sS -X POST "$INVOCATION_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "$REQUEST_BODY") || {
    echo "❌ Failed to contact runtime endpoint."
    exit 1
  }

echo "📊 Agent response:"
RAW_RESPONSE="$RAW_RESPONSE" python3 - <<'PY'
import json, os, sys

raw = os.environ.get("RAW_RESPONSE", "")
parts = []
for line in raw.splitlines():
    line = line.strip()
    if not line or not line.startswith("data: "):
        continue
    payload = line[6:]
    try:
        obj = json.loads(payload)
    except Exception:
        parts.append(payload)
        continue
    if isinstance(obj, dict) and isinstance(obj.get("text"), str):
        parts.append(obj["text"])
    elif isinstance(obj, str):
        parts.append(obj)
    else:
        parts.append(payload)

transcript = "".join(parts).strip()
if not transcript:
    # Not SSE — print whatever the server returned as-is.
    print(raw)
else:
    print(transcript)
PY

echo "✅ Test completed!"
