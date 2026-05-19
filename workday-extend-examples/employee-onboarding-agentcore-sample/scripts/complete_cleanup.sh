#!/bin/bash
set -e

# Amazon Bedrock HR Agent Demo - Complete Cleanup Script
# This script removes the AWS resources that deploy.sh creates.
#
# Discovery strategy (in priority order):
#   1. Tag query — any resource carrying Sample=<SAMPLE_ID> is fair game.
#   2. Exact name / IAM path match — for resources we own but can't tag.
#   3. Suffix match against the agent's full (unique) name — for toolkit-
#      auto-created resources (ECR, CodeBuild, CloudWatch) whose names we
#      only partially control.
#
# Two account-wide, shared AgentCore resources are deliberately NOT deleted:
#   - The S3 bucket `bedrock-agentcore-codebuild-sources-<account>-<region>`.
#   - The service-linked role `AWSServiceRoleForBedrockAgentCoreRuntimeIdentity`.
# Both are shared across every AgentCore deployment in the account; deleting
# them from this sample's cleanup could break other AgentCore work. Remove
# them by hand if you really want to — see SECURITY.md.

# Sample identity (must match deploy.sh)
SAMPLE_ID="sample-amazon-bedrock-agentcore-employee-onboarding"
RESOURCE_PREFIX="bedrock-employee-onboarding"
AGENT_NAME="employee_onboarding"
IAM_PATH="/${RESOURCE_PREFIX}/"
SAMPLE_TAG_KEY="Sample"
SAMPLE_TAG_VALUE="$SAMPLE_ID"

echo "🧹 Amazon Bedrock HR Agent Demo - Complete Cleanup"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI and configure credentials."
    exit 1
fi

# Check region
REGION=$(aws configure get region)
if [ "$REGION" != "us-east-1" ]; then
    print_warning "AWS region is $REGION, but this demo should be deployed in us-east-1"
    echo "   Please run: aws configure set region us-east-1"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Cleanup cancelled"
        exit 1
    fi
fi

print_status "Prerequisites check passed"

# Confirm cleanup
echo ""
print_warning "This will delete resources created by this sample's deploy.sh:"
echo "   - Agent runtime: $AGENT_NAME"
echo "   - AgentCore Gateway + MCP targets (name-prefix match)"
echo "   - AgentCore Memory (STM) for this agent"
echo "   - Cognito user pool + domain (tagged by deploy.sh)"
echo "   - Lambda function: ${RESOURCE_PREFIX}-hr-tools-mcp"
echo "   - IAM roles at path $IAM_PATH + toolkit-created roles"
echo "   - ECR repository, CodeBuild project, CloudWatch log groups"
echo "   - Tagged S3 buckets"
echo "   - Custom IAM policies matching this agent"
echo "   - Local files: .env, .bedrock_agentcore.yaml"
echo ""
print_info "The following are account-wide shared resources and will NOT be deleted:"
echo "   - S3 bucket bedrock-agentcore-codebuild-sources-<account>-<region>"
echo "   - Service-linked role AWSServiceRoleForBedrockAgentCoreRuntimeIdentity"
echo ""
read -p "Proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Cleanup cancelled"
    exit 1
fi

# Install AgentCore toolkit if not present
echo "📦 Ensuring AgentCore toolkit is available..."
if [ -f "src/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null  # Virtualenv activate script; not a static input
    source src/.venv/bin/activate && python3 -m pip install bedrock-agentcore-starter-toolkit --quiet
else
    print_warning "Local virtualenv not found; installing toolkit with system Python"
    python3 -m pip install --quiet --upgrade bedrock-agentcore-starter-toolkit
fi

# Function to safely delete resources with error handling
safe_delete() {
    local resource_type="$1"
    local resource_name="$2"
    shift 2
    
    echo "🗑️  Deleting $resource_type: $resource_name"
    if "$@" 2>/dev/null; then
        print_status "$resource_type deleted successfully"
    else
        print_warning "$resource_type deletion failed or resource not found"
    fi
}

# 0. Remove the AgentCore Runtime registration for THIS sample.
#    We identify it by the exact name deploy.sh chose. Tag-based lookup
#    isn't wired up yet for the bedrock-agentcore-control TagResource API
#    across all toolkit versions, so we fall back to exact-name match.
echo ""
echo "🏃 Removing AgentCore Runtime registration..."

AGENT_NAME_FOR_CLEANUP="$AGENT_NAME" python3 <<'PYEOF'
import os
import sys
import time

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError as exc:
    print(f"ℹ️ boto3 not available yet ({exc}); skipping AgentCore runtime step")
    sys.exit(0)

agent_name = os.environ["AGENT_NAME_FOR_CLEANUP"]

try:
    control = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
except Exception as exc:
    print(f"ℹ️ Cannot create bedrock-agentcore-control client ({exc}); skipping")
    sys.exit(0)

try:
    runtimes = control.list_agent_runtimes().get("agentRuntimes", [])
except (BotoCoreError, ClientError) as exc:
    print(f"ℹ️ list_agent_runtimes failed ({exc}); skipping")
    sys.exit(0)

# Exact-name match for the runtime deploy.sh creates. No substring matches;
# if a reader renamed the agent they'll need to clean up by hand.
target = [r for r in runtimes if (r.get("agentRuntimeName") or "") == agent_name]

if not target:
    print(f"ℹ️ No AgentCore runtime named '{agent_name}' found")
    sys.exit(0)

for r in target:
    runtime_id = r.get("agentRuntimeId")
    name = r.get("agentRuntimeName")
    status = r.get("status")

    if status == "DELETING":
        print(f"🗑️  AgentCore runtime already deleting: {name} ({runtime_id})")
    else:
        print(f"🗑️  Deleting AgentCore runtime: {name} ({runtime_id})")

        # Delete any non-default endpoints first
        try:
            endpoints = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id).get("runtimeEndpoints", [])
        except (BotoCoreError, ClientError):
            endpoints = []
        for ep in endpoints:
            ep_name = ep.get("name")
            if not ep_name or ep_name == "DEFAULT":
                continue
            try:
                control.delete_agent_runtime_endpoint(agentRuntimeId=runtime_id, endpointName=ep_name)
                print(f"   ✅ Deleted endpoint: {ep_name}")
            except (BotoCoreError, ClientError) as exc:
                print(f"   ⚠️ Endpoint {ep_name} delete failed: {exc}")

        try:
            control.delete_agent_runtime(agentRuntimeId=runtime_id)
            print("   ✅ Delete requested")
        except (BotoCoreError, ClientError) as exc:
            print(f"   ⚠️ Runtime delete failed: {exc}")
            continue

    # Poll until gone (runtime deletion is async; takes ~30-60s typically)
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            current = control.get_agent_runtime(agentRuntimeId=runtime_id)
            current_status = current.get("status")
            print(f"   ...status: {current_status}")
            if current_status not in ("DELETING", "DELETE_PENDING"):
                break
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                print(f"   ✅ Runtime fully deleted")
                break
            print(f"   ⚠️ Error polling runtime: {exc}")
            break
        time.sleep(10)
    else:
        print(f"   ⚠️ Timed out waiting for runtime {runtime_id} to fully delete")

# Let the control plane release dependent resources before IAM cleanup runs
time.sleep(5)
PYEOF

# 0b. Clean up AgentCore Gateways tagged for this sample.
#     Each deploy.sh run creates a new gateway with a random suffix. If the
#     user deployed multiple times without cleaning up, there may be several.
#     We find them by tag (same as Cognito pools in step 4).
echo ""
echo "🌐 Cleaning up AgentCore Gateways..."
SAMPLE_TAG_KEY="$SAMPLE_TAG_KEY" \
SAMPLE_TAG_VALUE="$SAMPLE_TAG_VALUE" \
RESOURCE_PREFIX="$RESOURCE_PREFIX" \
python3 <<'PYEOF'
import os
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("ℹ️ boto3 not available; skipping gateway cleanup")
    sys.exit(0)

tag_key = os.environ["SAMPLE_TAG_KEY"]
tag_value = os.environ["SAMPLE_TAG_VALUE"]
resource_prefix = os.environ["RESOURCE_PREFIX"]

try:
    client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
except Exception as exc:
    print(f"ℹ️ Cannot create bedrock-agentcore-control client ({exc}); skipping")
    sys.exit(0)

# Paginate through all gateways
all_gateways = []
try:
    resp = client.list_gateways()
    all_gateways.extend(resp.get("items", []))
    while resp.get("nextToken"):
        resp = client.list_gateways(nextToken=resp["nextToken"])
        all_gateways.extend(resp.get("items", []))
except (BotoCoreError, ClientError) as exc:
    print(f"ℹ️ list_gateways failed ({exc}); skipping")
    sys.exit(0)

deleted = 0
for gw in all_gateways:
    gw_id = gw.get("gatewayId", "")
    gw_name = gw.get("name", "")
    if not gw_id:
        continue

    # Match by name prefix (deploy.sh names them <RESOURCE_PREFIX>-gateway-<hex>)
    # This catches both tagged and untagged gateways from this sample.
    if not gw_name.startswith(resource_prefix):
        continue

    # Double-check via tags if possible (best effort — skip if tag lookup fails)
    try:
        detail = client.get_gateway(gatewayIdentifier=gw_id)
        gw_arn = detail.get("gatewayArn", "")
        if gw_arn:
            tags = client.list_tags_for_resource(resourceArn=gw_arn).get("tags", {})
            if tags and tags.get(tag_key) != tag_value:
                # Has tags but not ours — skip
                print(f"   ⏭️  Skipping {gw_name} (tagged for a different sample)")
                continue
    except (BotoCoreError, ClientError):
        pass  # Can't verify tags; proceed with name-based match

    # Delete targets first
    try:
        targets_resp = client.list_gateway_targets(gatewayIdentifier=gw_id)
        targets = targets_resp.get("items", targets_resp.get("targets", []))
        for t in targets:
            tid = t.get("targetId", "")
            if tid:
                client.delete_gateway_target(gatewayIdentifier=gw_id, targetId=tid)
                print(f"   ✅ Deleted gateway target: {tid}")
        # Target deletion is async; wait for propagation before deleting gateway
        if targets:
            import time
            time.sleep(5)
    except (BotoCoreError, ClientError) as exc:
        print(f"   ⚠️ Failed to delete targets for {gw_name}: {exc}")

    # Delete gateway
    try:
        client.delete_gateway(gatewayIdentifier=gw_id)
        print(f"   ✅ Deleted gateway: {gw_name} ({gw_id})")
        deleted += 1
    except (BotoCoreError, ClientError) as exc:
        print(f"   ⚠️ Failed to delete gateway {gw_name}: {exc}")

if deleted == 0:
    print("ℹ️ No AgentCore Gateways for this sample found")
else:
    print(f"   ✅ Deleted {deleted} gateway(s)")
PYEOF

# 0c. Clean up AgentCore Memory resources for this sample's agent.
#     The toolkit creates a memory (STM) per agent that persists after
#     runtime deletion. Match by name prefix against the agent name.
echo ""
echo "🧠 Cleaning up AgentCore Memory resources..."
AGENT_NAME="$AGENT_NAME" python3 <<'PYEOF'
import os
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("ℹ️ boto3 not available; skipping memory cleanup")
    sys.exit(0)

agent_name = os.environ["AGENT_NAME"]

try:
    client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
except Exception as exc:
    print(f"ℹ️ Cannot create client ({exc}); skipping")
    sys.exit(0)

try:
    resp = client.list_memories()
    memories = resp.get("memories", resp.get("items", []))
except (BotoCoreError, ClientError) as exc:
    print(f"ℹ️ list_memories failed ({exc}); skipping")
    sys.exit(0)

deleted = 0
for mem in memories:
    mem_id = mem.get("id", mem.get("memoryId", ""))
    if not mem_id:
        continue
    # Match by agent name prefix (toolkit names them <agent_name>_mem-<suffix>)
    if agent_name not in mem_id:
        continue
    try:
        client.delete_memory(memoryId=mem_id)
        print(f"   ✅ Deleted memory: {mem_id}")
        deleted += 1
    except (BotoCoreError, ClientError) as exc:
        print(f"   ⚠️ Failed to delete memory {mem_id}: {exc}")

if deleted == 0:
    print("ℹ️ No AgentCore Memory resources for this sample found")
PYEOF

# 1. Clean up ECR repositories for this sample's agent.
#    Toolkit names the repo bedrock-agentcore-<agent-name>; exact-contains
#    against the unique agent name is effectively an exact match.
echo ""
echo "📦 Cleaning up ECR repositories..."
ECR_REPOS=$(aws ecr describe-repositories --region us-east-1 --query "repositories[?contains(repositoryName, '$AGENT_NAME')].repositoryName" --output text 2>/dev/null || echo "")
if [ -n "$ECR_REPOS" ]; then
    for repo in $ECR_REPOS; do
        safe_delete "ECR repository" "$repo" aws ecr delete-repository --repository-name "$repo" --region us-east-1 --force
    done
else
    print_info "No ECR repositories for this sample found"
fi

# 2. Clean up CodeBuild projects for this sample's agent
echo ""
echo "🏗️  Cleaning up CodeBuild projects..."
CODEBUILD_PROJECTS=$(aws codebuild list-projects --region us-east-1 --query "projects[?contains(@, '$AGENT_NAME')]" --output text 2>/dev/null || echo "")
if [ -n "$CODEBUILD_PROJECTS" ]; then
    for project in $CODEBUILD_PROJECTS; do
        safe_delete "CodeBuild project" "$project" aws codebuild delete-project --name "$project" --region us-east-1
    done
else
    print_info "No CodeBuild projects for this sample found"
fi

# 3. Clean up CloudWatch log groups for this sample's agent
echo ""
echo "📊 Cleaning up CloudWatch log groups..."
LOG_GROUPS=$(aws logs describe-log-groups --region us-east-1 --query "logGroups[?contains(logGroupName, '$AGENT_NAME')].logGroupName" --output text 2>/dev/null || echo "")
if [ -n "$LOG_GROUPS" ]; then
    for log_group in $LOG_GROUPS; do
        safe_delete "CloudWatch log group" "$log_group" aws logs delete-log-group --log-group-name "$log_group" --region us-east-1
    done
else
    print_info "No CloudWatch log groups for this sample found"
fi

# 4. Clean up Cognito User Pools by tag (fall back to name if untagged).
echo ""
echo "🔐 Cleaning up Cognito User Pools..."
# Enumerate pools and inspect each one's tags — the list-user-pools API
# doesn't filter by tag. Only delete pools carrying our Sample tag.
USER_POOLS_ALL=$(aws cognito-idp list-user-pools --max-results 50 --region us-east-1 --query "UserPools[].Id" --output text 2>/dev/null || echo "")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
USER_POOLS=""
for pool_id in $USER_POOLS_ALL; do
    if [ -z "$pool_id" ] || [ -z "$ACCOUNT_ID" ]; then continue; fi
    POOL_TAG=$(aws cognito-idp list-tags-for-resource \
        --resource-arn "arn:aws:cognito-idp:us-east-1:${ACCOUNT_ID}:userpool/${pool_id}" \
        --region us-east-1 \
        --query "Tags.${SAMPLE_TAG_KEY}" --output text 2>/dev/null || echo "")
    if [ "$POOL_TAG" = "$SAMPLE_TAG_VALUE" ]; then
        USER_POOLS="$USER_POOLS $pool_id"
    fi
done
if [ -n "$USER_POOLS" ]; then
    for pool_id in $USER_POOLS; do
        echo "🗑️  Processing Cognito User Pool: $pool_id"
        
        # Get pool name for better logging
        POOL_NAME=$(aws cognito-idp describe-user-pool --user-pool-id "$pool_id" --region us-east-1 --query "UserPool.Name" --output text 2>/dev/null || echo "unknown")
        
        # First delete the domain if it exists
        DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id "$pool_id" --region us-east-1 --query "UserPool.Domain" --output text 2>/dev/null || echo "")
        if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "None" ] && [ "$DOMAIN" != "null" ]; then
            echo "🗑️  Deleting Cognito domain: $DOMAIN"
            aws cognito-idp delete-user-pool-domain --domain "$DOMAIN" --user-pool-id "$pool_id" --region us-east-1 2>/dev/null || print_warning "Domain deletion failed for $DOMAIN"
            sleep 5  # Wait for domain deletion to complete
        fi
        
        # Then delete the user pool
        safe_delete "Cognito User Pool" "$POOL_NAME ($pool_id)" aws cognito-idp delete-user-pool --user-pool-id "$pool_id" --region us-east-1
    done
else
    print_info "No tagged Cognito User Pools for this sample found"
fi

# 5. Clean up IAM roles. We delete in two groups:
#    (a) roles created by THIS sample at path IAM_PATH — exact path match, safe.
#    (b) toolkit-auto-created roles tied to THIS sample's agent name —
#        matched by the unique agent name.
echo ""
echo "🔐 Cleaning up IAM roles..."
IAM_ROLES_SAMPLE=$(aws iam list-roles --path-prefix "$IAM_PATH" --query "Roles[].RoleName" --output text 2>/dev/null || echo "")
IAM_ROLES_TOOLKIT=$(aws iam list-roles --query "Roles[?contains(RoleName, '$AGENT_NAME')].RoleName" --output text 2>/dev/null || echo "")
IAM_ROLES=$(echo "$IAM_ROLES_SAMPLE $IAM_ROLES_TOOLKIT" | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ')
if [ -n "$IAM_ROLES" ]; then
    for role in $IAM_ROLES; do
        echo "🗑️  Processing IAM role: $role"
        
        # Detach managed policies
        ATTACHED_POLICIES=$(aws iam list-attached-role-policies --role-name "$role" --query "AttachedPolicies[].PolicyArn" --output text 2>/dev/null || echo "")
        for policy_arn in $ATTACHED_POLICIES; do
            if [ -n "$policy_arn" ]; then
                safe_delete "attached policy" "$policy_arn from $role" aws iam detach-role-policy --role-name "$role" --policy-arn "$policy_arn"
            fi
        done
        
        # Delete inline policies
        INLINE_POLICIES=$(aws iam list-role-policies --role-name "$role" --query "PolicyNames" --output text 2>/dev/null || echo "")
        for policy_name in $INLINE_POLICIES; do
            if [ -n "$policy_name" ]; then
                safe_delete "inline policy" "$policy_name from $role" aws iam delete-role-policy --role-name "$role" --policy-name "$policy_name"
            fi
        done
        
        # Delete the role
        safe_delete "IAM role" "$role" aws iam delete-role --role-name "$role"
    done
else
    print_info "No IAM roles for this sample found"
fi

# 6. Clean up S3 buckets tagged for this sample.
#    We deliberately do NOT delete the account-wide toolkit build bucket
#    (bedrock-agentcore-codebuild-sources-<account>-<region>); it's shared
#    across every AgentCore deployment. See SECURITY.md.
echo ""
echo "🪣 Cleaning up S3 buckets tagged Sample=${SAMPLE_ID}..."
S3_BUCKETS_ALL=$(aws s3api list-buckets --query "Buckets[].Name" --output text 2>/dev/null || echo "")
S3_BUCKETS=""
for bucket in $S3_BUCKETS_ALL; do
    if [ -z "$bucket" ]; then continue; fi
    # Skip the account-wide AgentCore toolkit build bucket explicitly.
    case "$bucket" in
        bedrock-agentcore-codebuild-sources-*)
            continue
            ;;
    esac
    BUCKET_TAG=$(aws s3api get-bucket-tagging --bucket "$bucket" \
        --query "TagSet[?Key=='${SAMPLE_TAG_KEY}'] | [0].Value" \
        --output text 2>/dev/null || echo "")
    if [ "$BUCKET_TAG" = "$SAMPLE_TAG_VALUE" ]; then
        S3_BUCKETS="$S3_BUCKETS $bucket"
    fi
done

if [ -n "$S3_BUCKETS" ]; then
    for bucket in $S3_BUCKETS; do
        BUCKET_REGION=$(aws s3api get-bucket-location --bucket "$bucket" --query "LocationConstraint" --output text 2>/dev/null || echo "")
        if [ -z "$BUCKET_REGION" ] || [ "$BUCKET_REGION" = "None" ] || [ "$BUCKET_REGION" = "null" ]; then
            BUCKET_REGION="us-east-1"
        fi

        echo "🗑️  Cleaning S3 bucket: $bucket (region: $BUCKET_REGION)"
        aws s3 rm "s3://$bucket" --recursive --region "$BUCKET_REGION" 2>/dev/null || print_warning "Failed to empty bucket $bucket"
        safe_delete "S3 bucket" "$bucket" aws s3 rb "s3://$bucket" --region "$BUCKET_REGION"
    done
else
    print_info "No tagged S3 buckets for this sample found"
fi
print_info "(Skipped: bedrock-agentcore-codebuild-sources-<account>-<region> is shared across AgentCore deployments.)"

# 7. Clean up THIS sample's Lambda function (exact name match)
echo ""
print_info "Checking for Lambda function..."
LAMBDA_NAME_EXPECTED="${RESOURCE_PREFIX}-hr-tools-mcp"
if aws lambda get-function --function-name "$LAMBDA_NAME_EXPECTED" --region us-east-1 >/dev/null 2>&1; then
    safe_delete "Lambda function" "$LAMBDA_NAME_EXPECTED" aws lambda delete-function --function-name "$LAMBDA_NAME_EXPECTED" --region us-east-1
else
    print_info "No Lambda function named '$LAMBDA_NAME_EXPECTED' found"
fi

# 8. Service-linked role handling. The AgentCore SLR is created once per
#    account and shared across every AgentCore deployment. Deleting it could
#    break other AgentCore work, so we do NOT delete it here. If this is the
#    last AgentCore sample in your account and you want it gone, run:
#        aws iam delete-service-linked-role \
#          --role-name AWSServiceRoleForBedrockAgentCoreRuntimeIdentity
echo ""
print_info "Skipping account-wide service-linked role AWSServiceRoleForBedrockAgentCoreRuntimeIdentity"
print_info "(It is shared across AgentCore deployments; delete by hand if desired.)"

# 9. Clean up local configuration files
echo ""
echo "📁 Cleaning up local configuration files..."
LOCAL_FILES=(".env" ".bedrock_agentcore.yaml")
for file in "${LOCAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        print_status "Removed local file: $file"
    else
        print_info "Local file not found: $file"
    fi
done

# 10. Clean up any remaining custom IAM policies tied to this sample.
#     Match only on the unique agent name. The old broad matches ('Gateway',
#     'Welcome') are gone — they were catching unrelated policies.
echo ""
echo "📋 Cleaning up custom IAM policies..."
CUSTOM_POLICIES=$(aws iam list-policies --scope Local --query "Policies[?contains(PolicyName, '$AGENT_NAME') || contains(PolicyName, '$RESOURCE_PREFIX')].PolicyName" --output text 2>/dev/null || echo "")
if [ -n "$CUSTOM_POLICIES" ]; then
    for policy in $CUSTOM_POLICIES; do
        # Get policy ARN
        POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='$policy'].Arn" --output text 2>/dev/null || echo "")
        if [ -n "$POLICY_ARN" ]; then
            echo "🗑️  Processing IAM policy: $policy"
            
            # Check if policy is attached to any entities
            ATTACHED_ROLES=$(aws iam list-entities-for-policy --policy-arn "$POLICY_ARN" --query "PolicyRoles[].RoleName" --output text 2>/dev/null || echo "")
            ATTACHED_USERS=$(aws iam list-entities-for-policy --policy-arn "$POLICY_ARN" --query "PolicyUsers[].UserName" --output text 2>/dev/null || echo "")
            ATTACHED_GROUPS=$(aws iam list-entities-for-policy --policy-arn "$POLICY_ARN" --query "PolicyGroups[].GroupName" --output text 2>/dev/null || echo "")
            
            # Detach from roles
            for role in $ATTACHED_ROLES; do
                if [ -n "$role" ]; then
                    safe_delete "policy attachment" "$policy from role $role" aws iam detach-role-policy --role-name "$role" --policy-arn "$POLICY_ARN"
                fi
            done
            
            # Detach from users
            for user in $ATTACHED_USERS; do
                if [ -n "$user" ]; then
                    safe_delete "policy attachment" "$policy from user $user" aws iam detach-user-policy --user-name "$user" --policy-arn "$POLICY_ARN"
                fi
            done
            
            # Detach from groups
            for group in $ATTACHED_GROUPS; do
                if [ -n "$group" ]; then
                    safe_delete "policy attachment" "$policy from group $group" aws iam detach-group-policy --group-name "$group" --policy-arn "$POLICY_ARN"
                fi
            done
            
            # Delete all policy versions except default
            VERSIONS=$(aws iam list-policy-versions --policy-arn "$POLICY_ARN" --query "Versions[?!IsDefaultVersion].VersionId" --output text 2>/dev/null || echo "")
            for version in $VERSIONS; do
                if [ -n "$version" ]; then
                    safe_delete "policy version" "$version of $policy" aws iam delete-policy-version --policy-arn "$POLICY_ARN" --version-id "$version"
                fi
            done
            
            # Delete the policy
            safe_delete "IAM policy" "$policy" aws iam delete-policy --policy-arn "$POLICY_ARN"
        fi
    done
else
    print_info "No custom IAM policies for this sample found"
fi

echo ""
echo "🎉 Cleanup Finished!"
echo "===================="
echo ""
print_status "This sample's resources have been cleaned up."
print_info "Deliberately skipped (shared across AgentCore deployments):"
echo "   - S3 bucket bedrock-agentcore-codebuild-sources-<account>-<region>"
echo "   - Service-linked role AWSServiceRoleForBedrockAgentCoreRuntimeIdentity"
echo ""
print_info "You can now safely run a fresh deployment:"
echo "   make deploy  (or ./scripts/deploy.sh)"
echo ""
print_info "To verify cleanup was successful, run:"
echo "   make verify-clean  (or source src/.venv/bin/activate && python3 scripts/verify_cleanup.py)"