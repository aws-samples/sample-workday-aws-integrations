#!/bin/bash
set -e

# Amazon Bedrock HR Agent Demo - Deployment Script
# This script automates the deployment of AgentCore Gateway and Runtime with OAuth2 authentication
#
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ STRUCTURE                                                                   │
# │                                                                             │
# │ This script is organized into phases. Each phase is a function:             │
# │   1. parse_arguments        — CLI flags (--model, --help)                   │
# │   2. check_prerequisites    — AWS CLI, Python, region, credentials          │
# │   3. install_dependencies   — venv, pip, toolkit                            │
# │   4. deploy_gateway         — create or reuse AgentCore Gateway + Cognito   │
# │   5. configure_runtime      — agentcore configure with JWT authorizer       │
# │   6. deploy_runtime         — agentcore deploy (builds container)           │
# │   7. deploy_lambda          — Lambda function for HR tools                  │
# │   8. register_mcp_target    — register Lambda with Gateway                  │
# │   9. generate_env_file      — write .env for local CLI use                  │
# │  10. print_summary          — success banner with next steps                │
# │                                                                             │
# │ Scroll to the bottom for the main execution flow.                           │
# └─────────────────────────────────────────────────────────────────────────────┘

# --------------------------------------------------------------------------
# Sample identity. All resources created by this script carry the tag
# Sample=<SAMPLE_ID> and use <RESOURCE_PREFIX> (or its underscore variant)
# in their names. The companion cleanup script uses these to find resources
# exactly, without falling back to fuzzy substring matches.
# --------------------------------------------------------------------------
SAMPLE_ID="sample-amazon-bedrock-agentcore-employee-onboarding"
RESOURCE_PREFIX="bedrock-employee-onboarding"
IAM_PATH="/${RESOURCE_PREFIX}/"
SAMPLE_TAG_KEY="Sample"
SAMPLE_TAG_VALUE="$SAMPLE_ID"

echo "🚀 Amazon Bedrock HR Agent Demo - Deployment"
echo "============================================="
echo "This script will deploy:"
echo "  - AgentCore Gateway with Cognito OAuth2"
echo "  - AgentCore Runtime with JWT authorizer"
echo "  - Complete OAuth2 authentication setup"
echo ""

# Parse command-line arguments
MODEL_ID="us.anthropic.claude-haiku-4-5-20251001-v1:0"  # Default
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_ID="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--model MODEL_ID]"
            echo ""
            echo "Options:"
            echo "  --model MODEL_ID    Bedrock model ID to use for the agent"
            echo "                      Default: us.anthropic.claude-haiku-4-5-20251001-v1:0"
            echo ""
            echo "Examples:"
            echo "  $0                  # Full cloud deployment"
            echo "  $0 --model us.anthropic.claude-sonnet-4-5-20250929-v1:0"
            echo ""
            echo "Local development (no cloud deployment):"
            echo "  agentcore configure -e src/agentcore/onboarding_app.py"
            echo "  agentcore deploy --local"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate MODEL_ID is not empty after parsing
if [ -z "$MODEL_ID" ]; then
    echo "❌ Error: MODEL_ID cannot be empty"
    exit 1
fi

echo "📋 Using model: $MODEL_ID"
echo ""

# ==========================================================================
# PHASE 1: Utilities
# ==========================================================================

run_with_sudo() {
    if command -v sudo &> /dev/null; then
        sudo "$@"
    else
        "$@"
    fi
}

attempt_python_install() {
    echo "⚠️  Python 3.10 or newer is required for this deployment."
    read -r -p "   Attempt automatic installation of Python 3.11 now? [y/N] " reply
    case "$reply" in
        [yY][eE][sS]|[yY])
            if command -v dnf &> /dev/null; then
                echo "   Installing Python 3.11 using dnf..."
                run_with_sudo dnf install -y python3.11 python3.11-devel || return 1
            elif command -v apt-get &> /dev/null; then
                echo "   Installing Python 3.11 using apt-get..."
                run_with_sudo apt-get update || return 1
                run_with_sudo apt-get install -y python3.11 python3.11-venv python3.11-dev || return 1
            else
                echo "❌ Automatic Python installation is not supported on this platform."
                echo "   Please install Python 3.11 manually and re-run this script."
                return 1
            fi
            return 0
            ;;
        *)
            echo "❌ Python installation aborted by user."
            return 1
            ;;
    esac
}

select_python_cmd() {
    if [ -n "${PYTHON_CMD:-}" ] && command -v "$PYTHON_CMD" &> /dev/null; then
        return 0
    fi
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        return 0
    fi
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        return 0
    fi
    return 1
}

# ==========================================================================
# PHASE 2: Check Prerequisites
# ==========================================================================

echo "📋 Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI and configure credentials."
    exit 1
fi

# Check Python (prefer python3.11, fall back to python3)
PYTHON_INSTALL_ATTEMPTED=false
while true; do
    if ! select_python_cmd; then
        echo "❌ Python 3 not found on PATH."
        if [ "$PYTHON_INSTALL_ATTEMPTED" = false ] && attempt_python_install; then
            PYTHON_INSTALL_ATTEMPTED=true
            PYTHON_CMD=""
            continue
        fi
        exit 1
    fi

    PYTHON_VERSION=$("$PYTHON_CMD" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || echo "")
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ -n "$PYTHON_VERSION" ]; then
        if [ "$PYTHON_MAJOR" -gt 3 ]; then
            break
        fi
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            break
        fi
    fi

    echo "❌ Python $PYTHON_VERSION detected at ${PYTHON_CMD:-unknown}. Python 3.10+ is required."
    if [ "$PYTHON_INSTALL_ATTEMPTED" = false ] && attempt_python_install; then
        PYTHON_INSTALL_ATTEMPTED=true
        PYTHON_CMD=""
        continue
    fi
    exit 1
done

# Check region
REGION=$(aws configure get region 2>/dev/null || true)
if [ -z "$REGION" ]; then
    REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-}}
fi

if [ -z "$REGION" ]; then
    echo "❌ AWS region is not configured. This demo requires us-east-1."
    echo "   Please run: aws configure set region us-east-1"
    exit 1
fi

if [ "$REGION" != "us-east-1" ]; then
    echo "⚠️  Warning: AWS region is $REGION, but this demo requires us-east-1"
    echo "   Please run: aws configure set region us-east-1"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS credentials not configured or invalid."
    echo "   Please run: aws configure"
    exit 1
fi

echo "✅ Prerequisites check passed"

# ==========================================================================
# PHASE 3: Install Dependencies
# ==========================================================================

echo "📦 Installing dependencies..."
if [ ! -f "src/.venv/bin/activate" ]; then
    echo "   Creating virtual environment at src/.venv"
    "$PYTHON_CMD" -m venv src/.venv
fi
# shellcheck source=/dev/null  # Virtualenv activate script; not a static input
source src/.venv/bin/activate
pip install --quiet --upgrade pip
pip install -r src/agentcore/requirements.txt
pip install bedrock-agentcore-starter-toolkit

# ==========================================================================
# PHASE 4: Deploy Gateway (idempotent — reuses existing if present)
# ==========================================================================

echo "🌐 Deploying AgentCore Gateway..."
GATEWAY_NAME="${RESOURCE_PREFIX}-gateway"
echo "   Gateway name: $GATEWAY_NAME"

# Check if a gateway with this name already exists
EXISTING_GW=$("$PYTHON_CMD" -c "
import json, sys
try:
    import boto3
    client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    resp = client.list_gateways()
    for gw in resp.get('items', []):
        if gw.get('name') == '$GATEWAY_NAME' and gw.get('status') == 'READY':
            detail = client.get_gateway(gatewayIdentifier=gw['gatewayId'])
            print(json.dumps({
                'gatewayId': gw['gatewayId'],
                'gatewayArn': detail.get('gatewayArn', ''),
                'roleArn': detail.get('roleArn', ''),
            }))
            sys.exit(0)
except Exception:
    pass
print('')
")

if [ -n "$EXISTING_GW" ]; then
    echo "   ✅ Found existing gateway, reusing it"
    GATEWAY_ID=$(echo "$EXISTING_GW" | "$PYTHON_CMD" -c "import sys,json;d=json.load(sys.stdin);print(d.get('gatewayId',''))")
    GATEWAY_ARN=$(echo "$EXISTING_GW" | "$PYTHON_CMD" -c "import sys,json;d=json.load(sys.stdin);print(d.get('gatewayArn',''))")
    GATEWAY_ROLE_ARN=$(echo "$EXISTING_GW" | "$PYTHON_CMD" -c "import sys,json;d=json.load(sys.stdin);print(d.get('roleArn',''))")
    GATEWAY_URL="https://$GATEWAY_ID.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
    SKIP_MCP_REGISTRATION=false

    # Retrieve Cognito details from the existing gateway's authorizer config
    COGNITO_DETAILS=$("$PYTHON_CMD" -c "
import json, sys, re
try:
    import boto3
    client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    detail = client.get_gateway(gatewayIdentifier='$GATEWAY_ID')
    auth_config = detail.get('authorizerConfiguration', {})
    jwt_config = auth_config.get('customJWTAuthorizer', {})
    discovery_url = jwt_config.get('discoveryUrl', '')
    allowed_clients = jwt_config.get('allowedClients', [])
    # Extract user pool ID from discovery URL
    m = re.search(r'cognito-idp\.[^/]+\.amazonaws\.com/([^/]+)/', discovery_url)
    pool_id = m.group(1) if m else ''
    client_id = allowed_clients[0] if allowed_clients else ''
    print(json.dumps({'userPoolId': pool_id, 'clientId': client_id}))
except Exception as e:
    print('')
    sys.exit(0)
")
    if [ -n "$COGNITO_DETAILS" ]; then
        USER_POOL_ID=$(echo "$COGNITO_DETAILS" | "$PYTHON_CMD" -c "import sys,json;d=json.load(sys.stdin);print(d.get('userPoolId',''))")
        CLIENT_ID=$(echo "$COGNITO_DETAILS" | "$PYTHON_CMD" -c "import sys,json;d=json.load(sys.stdin);print(d.get('clientId',''))")
    fi
else
    # No existing gateway — create a new one
    GATEWAY_OUTPUT=$(agentcore create_mcp_gateway \
        --name "$GATEWAY_NAME" \
        --region us-east-1 2>&1)

    GATEWAY_EXIT_CODE=$?
    if [ $GATEWAY_EXIT_CODE -ne 0 ]; then
        echo "❌ Gateway deployment failed with exit code $GATEWAY_EXIT_CODE"
        echo "Output: $GATEWAY_OUTPUT"
        exit 1
    fi

    echo "✅ Gateway created: $GATEWAY_NAME"

    # Extract gateway details from output (supports both single and double quotes)
    GATEWAY_ID=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"gatewayId['\\\"]:\\s*['\\\"]([^'\\\"]+)\",data);print(m.group(1) if m else '')")
    GATEWAY_ARN=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Created Gateway:\\s*(arn:[^\\s]+)\",data);print(m.group(1) if m else '')")
    GATEWAY_ROLE_ARN=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Role already exists:\\s*(arn:[^\\s]+)\",data);print(m.group(1) if m else '')")
    GATEWAY_URL=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Gateway URL:\\s*(https://[^\\s]+)\",data);print(m.group(1) if m else '')")
    COGNITO_DOMAIN=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Created domain:\\s*([a-z0-9\\-]+)\",data);print(m.group(1) if m else '')")
    CLIENT_ID=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Created client:\\s*([A-Za-z0-9]+)\",data);print(m.group(1) if m else '')")
    USER_POOL_ID=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Created User Pool:\\s*(us-east-1_[A-Za-z0-9]+)\",data);print(m.group(1) if m else '')")

    if [ -z "$GATEWAY_URL" ] && [ -n "$GATEWAY_ID" ]; then
        GATEWAY_URL="https://$GATEWAY_ID.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
    fi

    if [ -z "$GATEWAY_ARN" ]; then
        GATEWAY_ARN=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"gatewayArn['\\\"]:\\s*['\\\"]([^'\\\"]+)\",data);print(m.group(1) if m else '')")
    fi

    if [ -z "$GATEWAY_ROLE_ARN" ]; then
        GATEWAY_ROLE_ARN=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"roleArn['\\\"]:\\s*['\\\"]([^'\\\"]+)\",data);print(m.group(1) if m else '')")
    fi

    SKIP_MCP_REGISTRATION=false
fi

if [ -z "$GATEWAY_ID" ] || [ -z "$GATEWAY_URL" ] || [ -z "$GATEWAY_ARN" ]; then
    echo "⚠️  Could not extract gateway details from output. Manual configuration may be required."
    SKIP_MCP_REGISTRATION=true
fi

# Wait for gateway to be fully ready
echo "⏳ Waiting for gateway to be ready..."
sleep 10

# Tag the gateway and its Cognito user pool so cleanup can find them by tag
# rather than by fuzzy name match. Best effort — a failure here doesn't stop
# the deployment, but cleanup may fall back to name-based discovery.
echo "🏷️  Tagging gateway and Cognito user pool with Sample=${SAMPLE_ID}..."
if [ -n "$GATEWAY_ARN" ]; then
    SAMPLE_TAG_KEY="$SAMPLE_TAG_KEY" \
    SAMPLE_TAG_VALUE="$SAMPLE_TAG_VALUE" \
    GATEWAY_ARN="$GATEWAY_ARN" \
    "$PYTHON_CMD" - <<'PYEOF' || echo "   ⚠️ Gateway tag best-effort failed (non-fatal)"
import os
try:
    import boto3
except ImportError:
    raise SystemExit("boto3 unavailable")
client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
client.tag_resource(
    resourceArn=os.environ["GATEWAY_ARN"],
    tags={os.environ["SAMPLE_TAG_KEY"]: os.environ["SAMPLE_TAG_VALUE"]},
)
print("   ✅ Tagged gateway")
PYEOF
fi

if [ -n "$USER_POOL_ID" ]; then
    aws cognito-idp tag-resource \
        --resource-arn "arn:aws:cognito-idp:us-east-1:$(aws sts get-caller-identity --query Account --output text):userpool/$USER_POOL_ID" \
        --tags "$SAMPLE_TAG_KEY=$SAMPLE_TAG_VALUE" \
        --region us-east-1 2>/dev/null \
        && echo "   ✅ Tagged Cognito user pool" \
        || echo "   ⚠️ Cognito user pool tag best-effort failed (non-fatal)"
fi

# Get Cognito client secret and configuration
echo "🔑 Retrieving Cognito client secret..."
if [ -n "$CLIENT_ID" ] && [ -n "$USER_POOL_ID" ]; then
    CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id "$USER_POOL_ID" \
        --client-id "$CLIENT_ID" \
        --region us-east-1 \
        --query "UserPoolClient.ClientSecret" \
        --output text 2>/dev/null || echo "")
    
    # Get the correct OAuth scope
    OAUTH_SCOPE=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id "$USER_POOL_ID" \
        --client-id "$CLIENT_ID" \
        --region us-east-1 \
        --query "UserPoolClient.AllowedOAuthScopes[0]" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$COGNITO_DOMAIN" ]; then
        COGNITO_DOMAIN=$(aws cognito-idp describe-user-pool \
            --user-pool-id "$USER_POOL_ID" \
            --region us-east-1 \
            --query "UserPool.Domain" \
            --output text 2>/dev/null || echo "")
    fi
fi

# ==========================================================================
# PHASE 5: Configure AgentCore Runtime
# ==========================================================================

echo "⚙️  Configuring AgentCore Runtime with OAuth2..."
# The toolkit derives observability resource names from AGENT_NAME with
# suffixes up to 34 characters (e.g. "_mem-<10-char-id>-traces-destination"),
# and the underlying service caps those names at 60 characters total.
# That leaves a 26-character budget for AGENT_NAME itself. Keep it short
# and decoupled from RESOURCE_PREFIX — the prefix stays long and descriptive
# for everything else (gateway, Lambda, IAM path, tag value).
AGENT_NAME="employee_onboarding"

# Guard against anyone bumping this past the budget again. The limit comes
# from the toolkit's observability name derivation, not an arbitrary choice.
AGENT_NAME_MAX=26
if [ ${#AGENT_NAME} -gt $AGENT_NAME_MAX ]; then
    echo "❌ AGENT_NAME is ${#AGENT_NAME} chars (max ${AGENT_NAME_MAX}). Shorten it to avoid a 60-char observability resource name failure." >&2
    exit 1
fi

# Ensure Gateway URL and ARN have values before continuing
if [ -z "$GATEWAY_URL" ]; then
    GATEWAY_URL=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Gateway URL:\\s*(https://[^\\s]+)\",data);print(m.group(1) if m else '')")
fi
if [ -z "$GATEWAY_ARN" ]; then
    GATEWAY_ARN=$(echo "$GATEWAY_OUTPUT" | "$PYTHON_CMD" -c "import sys,re;data=sys.stdin.read();data=re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data);m=re.search(r\"Created Gateway:\\s*(arn:[^\\s]+)\",data);print(m.group(1) if m else '')")
fi

# Create JWT authorizer configuration
if [ -n "$USER_POOL_ID" ] && [ -n "$CLIENT_ID" ]; then
    JWT_CONFIG='{"customJWTAuthorizer": {"discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/'$USER_POOL_ID'/.well-known/openid-configuration", "allowedClients": ["'$CLIENT_ID'"]}}'
    
    agentcore configure \
        --name "$AGENT_NAME" \
        --entrypoint "src/agentcore/onboarding_app.py" \
        --requirements-file "src/agentcore/requirements.txt" \
        --region us-east-1 \
        --authorizer-config "$JWT_CONFIG" \
        --non-interactive
else
    echo "⚠️  Could not configure OAuth2, using default IAM authorization"
    agentcore configure \
        --name "$AGENT_NAME" \
        --entrypoint "src/agentcore/onboarding_app.py" \
        --requirements-file "src/agentcore/requirements.txt" \
        --region us-east-1 \
        --non-interactive
fi

# Add MCP configuration to the YAML file after agent is configured
if [ -n "$GATEWAY_ARN" ]; then
    echo "🔗 Adding MCP gateway configuration to .bedrock_agentcore.yaml..."

    # Use Python to manipulate the YAML so we don't rely on BSD-vs-GNU sed
    # differences (macOS BSD sed's `a\` newline escaping silently concatenates
    # the inserted block onto adjacent lines, producing invalid YAML).
    GATEWAY_ARN="$GATEWAY_ARN" "$PYTHON_CMD" <<'PYEOF'
import os
import sys
from pathlib import Path

gateway_arn = os.environ["GATEWAY_ARN"].strip()
if not gateway_arn:
    sys.exit("GATEWAY_ARN is empty")

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not available; ensure the project virtualenv is active")

config_path = Path(".bedrock_agentcore.yaml")
data = yaml.safe_load(config_path.read_text()) or {}
default_agent = data.get("default_agent")
if not default_agent:
    sys.exit("No default_agent in .bedrock_agentcore.yaml")

agent = data.setdefault("agents", {}).setdefault(default_agent, {})
agent["mcp_configuration"] = {"gateway_arn": gateway_arn}

config_path.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
print(f"   Set mcp_configuration.gateway_arn for agent '{default_agent}'")
PYEOF

    # shellcheck disable=SC2181  # Exit code is from the heredoc Python block above; inlining not possible
    if [ $? -ne 0 ]; then
        echo "❌ Failed to write MCP configuration into .bedrock_agentcore.yaml"
        exit 1
    fi

    echo "✅ MCP configuration added to agent"
else
    echo "❌ Could not extract Gateway ARN - MCP integration may not work"
fi

# ==========================================================================
# PHASE 6: Deploy AgentCore Runtime (builds container via CodeBuild)
# ==========================================================================

# Pass --auto-update-on-conflict so re-runs after a partial failure update the
# existing agent in place instead of hitting ConflictException.
#
# --env injections pass the gateway URL and Cognito client-credentials into
# the container's environment. Without these, the deployed agent would have
# no way to know where its MCP gateway is or how to authenticate to it: the
# .env file this script writes lives on the developer's workstation, not in
# the packaged container. The agent needs only four Cognito fields for the
# client-credentials token flow (client_id, client_secret, token_endpoint,
# scope); user_pool_id and domain_prefix are not required.
echo "🏃 Deploying AgentCore Runtime..."
echo "🏗️  Building container image via CodeBuild (typically 5-8 minutes)..."
echo "   You can monitor progress in the AWS Console: CodeBuild → Build projects"
agentcore deploy --auto-update-on-conflict \
    --env "AGENTCORE_MCP_URL=${GATEWAY_URL}" \
    --env "COGNITO_CLIENT_ID=${CLIENT_ID}" \
    --env "COGNITO_CLIENT_SECRET=${CLIENT_SECRET}" \
    --env "COGNITO_TOKEN_ENDPOINT=https://${COGNITO_DOMAIN}.auth.us-east-1.amazoncognito.com/oauth2/token" \
    --env "COGNITO_SCOPE=${OAUTH_SCOPE}" \
    --env "MODEL_ID=${MODEL_ID}"

# shellcheck disable=SC2181  # Exit code is from the multi-line agentcore deploy above; inlining not practical
if [ $? -ne 0 ]; then
    echo "❌ Runtime deployment failed"
    exit 1
fi

echo "✅ Runtime deployed: $AGENT_NAME"

# Wait for deployment to complete
echo "⏳ Waiting for runtime to be ready..."
for i in {1..30}; do
    STATUS=$(agentcore status 2>/dev/null | grep -o "Ready\|Deploying\|Failed" | head -1 || echo "Unknown")
    if [ "$STATUS" = "Ready" ]; then
        echo "✅ Runtime is ready!"
        break
    elif [ "$STATUS" = "Failed" ]; then
        echo "❌ Runtime deployment failed"
        exit 1
    fi
    echo "   Status: $STATUS (attempt $i/30)"
    sleep 10
done

if [ "$STATUS" != "Ready" ]; then
    echo "⚠️  Runtime may still be starting. Check status with: agentcore status"
fi

# Tag the agent runtime so cleanup can find it by tag. Best effort.
echo "🏷️  Tagging agent runtime with Sample=${SAMPLE_ID}..."
RUNTIME_ARN_FOR_TAG=$(grep "agent_arn:" .bedrock_agentcore.yaml 2>/dev/null | sed 's/.*agent_arn: *//' || echo "")
if [ -n "$RUNTIME_ARN_FOR_TAG" ]; then
    SAMPLE_TAG_KEY="$SAMPLE_TAG_KEY" \
    SAMPLE_TAG_VALUE="$SAMPLE_TAG_VALUE" \
    RUNTIME_ARN_FOR_TAG="$RUNTIME_ARN_FOR_TAG" \
    "$PYTHON_CMD" - <<'PYEOF' || echo "   ⚠️ Runtime tag best-effort failed (non-fatal)"
import os
try:
    import boto3
except ImportError:
    raise SystemExit("boto3 unavailable")
client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
client.tag_resource(
    resourceArn=os.environ["RUNTIME_ARN_FOR_TAG"],
    tags={os.environ["SAMPLE_TAG_KEY"]: os.environ["SAMPLE_TAG_VALUE"]},
)
print("   ✅ Tagged agent runtime")
PYEOF
fi

# ==========================================================================
# PHASE 7: Deploy HR Tools Lambda (MCP Server)
# ==========================================================================

echo "🛠️  Deploying HR Tools Lambda (MCP Server)..."

# Create Lambda deployment package
TEMP_DIR=$(mktemp -d)
echo "   Creating deployment package in $TEMP_DIR"

# Copy HR tools code (preserve the tools/ package directory so the Lambda
# handler can import from tools.hr_tools).
mkdir -p "$TEMP_DIR/tools"
cp tools/__init__.py tools/hr_tools.py tools/mock_data.py "$TEMP_DIR/tools/"

# Create Lambda handler
# Copy Lambda handler (source lives at src/lambda_handler.py for readability)
cp src/lambda_handler.py "$TEMP_DIR/lambda_function.py"

# Create deployment zip
cd "$TEMP_DIR"
zip -r hr-tools-mcp.zip . > /dev/null
cd - > /dev/null

# Deploy Lambda function
LAMBDA_NAME="${RESOURCE_PREFIX}-hr-tools-mcp"
LAMBDA_ROLE_NAME="${RESOURCE_PREFIX}-lambda-role"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role${IAM_PATH}${LAMBDA_ROLE_NAME}"
echo "   Deploying Lambda function: $LAMBDA_NAME"

# Ensure the Lambda execution role exists BEFORE we create the function.
# Placing it at ${IAM_PATH} lets cleanup list it by path (exact, not fuzzy).
# We wait for AssumeRole propagation only when we had to create the role —
# otherwise the create-function call below runs immediately.
if aws iam get-role --role-name "$LAMBDA_ROLE_NAME" >/dev/null 2>&1; then
    echo "   Lambda execution role already exists: $LAMBDA_ROLE_NAME"
else
    echo "   Creating Lambda execution role at path ${IAM_PATH}..."
    aws iam create-role \
        --role-name "$LAMBDA_ROLE_NAME" \
        --path "$IAM_PATH" \
        --tags "Key=$SAMPLE_TAG_KEY,Value=$SAMPLE_TAG_VALUE" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }' > /dev/null

    aws iam attach-role-policy \
        --role-name "$LAMBDA_ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole > /dev/null

    # IAM needs ~10s for the new role to be assumable by the Lambda service
    echo "   Waiting for role to be assumable by Lambda..."
    sleep 10
fi

# Create or update the Lambda function
if aws lambda get-function --function-name "$LAMBDA_NAME" >/dev/null 2>&1; then
    echo "   Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$LAMBDA_NAME" \
        --zip-file "fileb://$TEMP_DIR/hr-tools-mcp.zip" \
        --region us-east-1 > /dev/null
else
    echo "   Creating new Lambda function..."
    aws lambda create-function \
        --function-name "$LAMBDA_NAME" \
        --runtime python3.11 \
        --role "$LAMBDA_ROLE_ARN" \
        --handler lambda_function.lambda_handler \
        --zip-file "fileb://$TEMP_DIR/hr-tools-mcp.zip" \
        --timeout 30 \
        --memory-size 256 \
        --tags "$SAMPLE_TAG_KEY=$SAMPLE_TAG_VALUE" \
        --region us-east-1 > /dev/null
fi

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_NAME" --region us-east-1 --query 'Configuration.FunctionArn' --output text)
echo "✅ Lambda deployed: $LAMBDA_ARN"

# Cleanup temp directory
rm -rf "$TEMP_DIR"

# Wait for gateway to be fully ready before registering Lambda
echo "⏳ Waiting for gateway to be ready for MCP target registration..."
sleep 15

# ==========================================================================
# PHASE 8: Register Lambda as MCP target
# ==========================================================================

if [ "$SKIP_MCP_REGISTRATION" = "true" ]; then
    echo "⚠️  Skipping MCP target registration due to missing gateway details"
    TARGET_OUTPUT="Skipped due to missing gateway ID"
    TARGET_ID=""
else
    echo "🔗 Registering HR Tools Lambda with Gateway..."
    echo "   Gateway ARN (for registration): ${GATEWAY_ARN:-'missing'}"
    echo "   Gateway Role ARN (for registration): ${GATEWAY_ROLE_ARN:-'missing'}"
    if [ -z "$GATEWAY_ARN" ] || [ -z "$GATEWAY_ROLE_ARN" ]; then
        echo "⚠️  Missing Gateway ARN or Role ARN, skipping MCP registration"
        TARGET_OUTPUT="Missing required ARNs"
        TARGET_ID=""
    else
        # Use set +e to prevent script exit on MCP registration failure
        set +e
        TOOL_SCHEMA=$(python3 - <<'PY'
from tools.hr_tools import HR_TOOLS
import json

def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items() if k != "enum"}
    if isinstance(obj, list):
        return [sanitize(item) for item in obj]
    return obj

inline_payload = [sanitize(tool_cls.get_schema()) for tool_cls in HR_TOOLS.values()]
print(json.dumps({"inlinePayload": inline_payload}))
PY
)
        printf -v TARGET_PAYLOAD '{"lambdaArn": "%s", "toolSchema": %s}' "$LAMBDA_ARN" "$TOOL_SCHEMA"
        TARGET_OUTPUT=$(agentcore gateway create-mcp-gateway-target \
            --gateway-arn "$GATEWAY_ARN" \
            --gateway-url "$GATEWAY_URL" \
            --role-arn "$GATEWAY_ROLE_ARN" \
            --name "${RESOURCE_PREFIX}-hr-tools-target" \
            --target-type lambda \
            --target-payload "$TARGET_PAYLOAD" \
            --region us-east-1 2>&1)
        MCP_EXIT_CODE=$?
        set -e
    fi
fi

if [ "$SKIP_MCP_REGISTRATION" = "true" ]; then
    echo "⚠️  MCP registration skipped - manual setup may be required"
    TARGET_ID=""
elif [ "${MCP_EXIT_CODE:-0}" -ne 0 ]; then
    echo "❌ MCP target registration failed:"
    echo "$TARGET_OUTPUT"
    echo "⚠️  Continuing with deployment - MCP tools may need manual registration"
    TARGET_ID=""
else
    # Extract target ID from the new command output format
    TARGET_ID=$(echo "$TARGET_OUTPUT" | grep -o "'targetId': '[^']*'" | cut -d"'" -f4 || echo "")
    if [ -z "$TARGET_ID" ]; then
        # Try alternative parsing if the format is different
        TARGET_ID=$(echo "$TARGET_OUTPUT" | grep -o "target.*created" | head -1 || echo "SUCCESS")
    fi
    echo "✅ MCP target registered: ${TARGET_ID:-'SUCCESS'}"
fi

echo "🛠️  HR Tools configured (employee directory + IT asset management)"
echo "   Lambda ARN: $LAMBDA_ARN"
echo "   Target ID: ${TARGET_ID:-'Manual registration required'}"
echo "   To disable: Set AGENT_USE_HR_TOOLS=false in .env"

# ==========================================================================
# PHASE 9: Generate .env file
# ==========================================================================

echo "⚙️  Generating .env configuration..."

# Debug output for troubleshooting
echo "   Extracted values:"
echo "   - Gateway URL: ${GATEWAY_URL:-'NOT_FOUND'}"
echo "   - Client ID: ${CLIENT_ID:-'NOT_FOUND'}"
echo "   - Client Secret: ${CLIENT_SECRET:+FOUND}"
echo "   - Cognito Domain: ${COGNITO_DOMAIN:-'NOT_FOUND'}"
echo "   - OAuth Scope: ${OAUTH_SCOPE:-'NOT_FOUND'}"

# Fail fast if critical credentials are missing — a silent success with
# broken credentials is worse than a clear failure.
if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$GATEWAY_URL" ]; then
    echo ""
    echo "❌ Critical credentials could not be extracted from gateway output."
    echo "   CLIENT_ID:     ${CLIENT_ID:-MISSING}"
    echo "   CLIENT_SECRET:  ${CLIENT_SECRET:+FOUND}${CLIENT_SECRET:-MISSING}"
    echo "   GATEWAY_URL:    ${GATEWAY_URL:-MISSING}"
    echo ""
    echo "   This usually means the agentcore CLI output format changed."
    echo "   Run 'make clean' and try again, or configure .env manually."
    echo "   See .env.example for the required variables."
    exit 1
fi

# Use extracted values or fallbacks
MCP_URL=${GATEWAY_URL:-""}
CLIENT_ID_VAL=${CLIENT_ID:-""}
CLIENT_SECRET_VAL=${CLIENT_SECRET:-""}
TOKEN_ENDPOINT="https://${COGNITO_DOMAIN}.auth.us-east-1.amazoncognito.com/oauth2/token"
OAUTH_SCOPE_VAL=${OAUTH_SCOPE:-""}

if [ -z "$COGNITO_DOMAIN" ]; then
    TOKEN_ENDPOINT=""
fi

# Get Agent ARN from AgentCore configuration
AGENT_ARN=$(grep "agent_arn:" .bedrock_agentcore.yaml 2>/dev/null | sed 's/.*agent_arn: *//' || echo "")
ENCODED_AGENT_ARN=""
if [ -n "$AGENT_ARN" ]; then
    ENCODED_AGENT_ARN=$(python3 -c "from urllib.parse import quote; import sys; print(quote(sys.argv[1], safe=''))" "$AGENT_ARN")
fi

# Generate .env file
cat > .env << EOF
# Generated by deploy.sh on $(date)
AWS_REGION="us-east-1"

# Model Configuration
MODEL_ID="$MODEL_ID"

# AgentCore Runtime Configuration
RUNTIME_AGENT_ARN="${AGENT_ARN:-}"

# OAuth2 Configuration
RUNTIME_CLIENT_ID="$CLIENT_ID_VAL"
RUNTIME_CLIENT_SECRET="$CLIENT_SECRET_VAL"
RUNTIME_TOKEN_ENDPOINT="$TOKEN_ENDPOINT"
RUNTIME_SCOPE="$OAUTH_SCOPE_VAL"

# Gateway Configuration (AGENTCORE_MCP_URL is the primary env var the agent reads)
AGENTCORE_MCP_URL="$MCP_URL"

# Feature Flags
AGENT_USE_HR_TOOLS="true"

# Deployment Details (for reference — not read by application code)
HR_TOOLS_LAMBDA_ARN="${LAMBDA_ARN:-}"
GATEWAY_ARN="${GATEWAY_ARN:-}"
TARGET_ID="${TARGET_ID:-}"
EOF

# ==========================================================================
# PHASE 10: Print Summary
# ==========================================================================

echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo ""
echo "📋 Deployed Resources:"
echo "   Model ID: $MODEL_ID"
echo "   HR Tools Lambda: ${LAMBDA_NAME:-'Not deployed'}"
echo "   Lambda ARN: ${LAMBDA_ARN:-'Not available'}"
echo "   Gateway: $GATEWAY_NAME"
echo "   Gateway ID: ${GATEWAY_ID:-'Check AWS Console'}"
echo "   Gateway ARN: ${GATEWAY_ARN:-'Not available'}"
echo "   MCP Target ID: ${TARGET_ID:-'Not registered'}"
echo "   Runtime: $AGENT_NAME"
echo "   User Pool: ${USER_POOL_ID:-'Check AWS Console'}"
echo "   Client ID: ${CLIENT_ID:-'Check AWS Console'}"
echo ""
echo "📄 Configuration Files:"
echo "   .env - Environment variables (✅ Generated)"
echo "   .bedrock_agentcore.yaml - Agent configuration (✅ Generated)"
echo ""

# Validate .env file
VALIDATION_FAILED=false
if [ -z "$CLIENT_SECRET_VAL" ]; then
    echo "❌ Client Secret not extracted"
    VALIDATION_FAILED=true
fi
if [ -z "$OAUTH_SCOPE_VAL" ]; then
    echo "❌ OAuth Scope not extracted"
    VALIDATION_FAILED=true
fi
if [ -z "$MCP_URL" ]; then
    echo "❌ Gateway URL not extracted"
    VALIDATION_FAILED=true
fi

if [ "$VALIDATION_FAILED" = "true" ]; then
    echo ""
    echo "⚠️  MANUAL STEP REQUIRED:"
    echo "   Some credentials could not be automatically extracted."
    echo "   Please check .env file and update any placeholder values."
    echo ""
else
    echo "✅ All OAuth2 credentials successfully extracted and configured"
    echo ""
    echo "🧪 Test the deployment:"
    echo "   source src/.venv/bin/activate"
    echo "   python3 src/cli/onboarding_cli.py \"test deployment\""
    echo ""
    if [ -n "$ENCODED_AGENT_ARN" ]; then
        echo "   # Runtime endpoint for external POST calls"
        echo "   https://bedrock-agentcore.$REGION.amazonaws.com/runtimes/$ENCODED_AGENT_ARN/invocations?qualifier=DEFAULT"
        echo ""
    fi
    echo "   # OAuth2 token endpoint (client credentials)"
    echo "   $TOKEN_ENDPOINT"
    echo "   Client ID: $CLIENT_ID_VAL"
    echo "   Client Secret: [written to .env — do not share]"
    echo "   Scope: $OAUTH_SCOPE_VAL"
    echo ""
fi
echo "🚀 Ready to test:"
echo ""
echo "   make smoke-test                    # Quick curl-based test"
echo "   make cli                           # CLI with formatted output"
echo "   make cli PROMPT=\"onboard jane doe as data scientist\""
echo ""
echo "   # Or run directly:"
echo "   ./scripts/test_agentcore_curl.sh \"onboard john smith as software engineer\""
echo "   source src/.venv/bin/activate && python3 src/cli/onboarding_cli.py \"onboard john smith\""
echo ""
echo "   # Check agent status"
echo "   agentcore status"
echo ""
echo "   ⚠️  Note: 'agentcore invoke' does NOT work with OAuth2-configured runtimes."
echo "   Use make smoke-test or make cli instead."
echo ""
echo "🔧 Troubleshooting:"
echo "   aws logs tail /aws/bedrock-agentcore/runtimes/$AGENT_NAME-*/DEFAULT --follow"
echo "   See TROUBLESHOOTING.md for common issues"
echo ""
echo "🧹 To clean up:  make clean           # (or ./scripts/complete_cleanup.sh)"
