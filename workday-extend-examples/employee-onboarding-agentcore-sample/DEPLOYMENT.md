# Deployment Guide

Step-by-step instructions for deploying the Amazon Bedrock AgentCore Employee Onboarding sample. For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md). For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Prerequisites

- Modern macOS (Monterey or later) **or** Amazon Linux 2023/AL2 on EC2
- Python 3.10+
- AWS CLI installed and configured (`aws configure`)
- `openssl` and `zip` on `PATH` (present by default on macOS and Amazon Linux)
- ~500 MB free disk space for the Python venv and build artifacts
- AWS account with:
  - Amazon Bedrock AgentCore available in `us-east-1` (scripts are hardcoded to this region)
  - Claude Haiku 4.5 model access enabled ([enable here](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess))

> **Windows** is untested and not recommended.

### Amazon Bedrock Model Access

Before running `make deploy`, enable Anthropic Claude Haiku 4.5 in the AWS Console:

1. Open the [Bedrock model access page](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) in `us-east-1`.
2. Click **Manage model access** and enable the Claude Haiku 4.5 model. Approval is usually instant.
3. If model access is missing, deployment succeeds but invocations fail with `AccessDeniedException`.

### AWS Credentials & Permissions

The simplest path: use an IAM principal with `AdministratorAccess` in a sandbox account.

> ⚠️ **Security note:** `AdministratorAccess` grants unrestricted access to all AWS services and resources. Use it only in a dedicated sandbox account that contains no production workloads or sensitive data. For shared accounts, CI pipelines, or any environment beyond personal experimentation, use the scoped policy below — it grants only the permissions this sample needs.

Do not run this in a shared or production account.

<details>
<summary>Scoped IAM policy (for CI, shared sandboxes, or security review)</summary>

**Bedrock AgentCore:**
- `bedrock-agentcore-control:CreateAgentRuntime`, `UpdateAgentRuntime`, `DeleteAgentRuntime`, `GetAgentRuntime`, `ListAgentRuntimes`, `ListAgentRuntimeEndpoints`, `DeleteAgentRuntimeEndpoint`
- `bedrock-agentcore-control:CreateGateway`, `DeleteGateway`, `CreateGatewayTarget`, `DeleteGatewayTarget`
- `bedrock-agentcore:InvokeAgentRuntime`

**Bedrock model access:**
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`

**IAM:**
- Create: `iam:CreateRole`, `PutRolePolicy`, `AttachRolePolicy`, `PassRole`, `CreateServiceLinkedRole`
- Delete: `iam:DeleteRole`, `DeleteRolePolicy`, `DetachRolePolicy`, `DeletePolicy`, `DeletePolicyVersion`, `ListAttachedRolePolicies`, `ListRolePolicies`, `DeleteServiceLinkedRole`, `GetServiceLinkedRoleDeletionStatus`, `ListPolicies`, `ListEntitiesForPolicy`

**Cognito:**
- `cognito-idp:CreateUserPool`, `DeleteUserPool`, `DescribeUserPool`, `ListUserPools`, `CreateUserPoolClient`, `DescribeUserPoolClient`, `CreateUserPoolDomain`, `DeleteUserPoolDomain`

**Lambda:**
- `lambda:CreateFunction`, `UpdateFunctionCode`, `DeleteFunction`, `GetFunction`, `ListFunctions`

**Supporting services:**
- `ecr:*` (AgentCore builds containers to dynamically named repositories)
- `codebuild:CreateProject`, `DeleteProject`, `ListProjects`, `StartBuild`
- `logs:CreateLogGroup`, `DescribeLogGroups`, `DeleteLogGroup`, `TagResource`
- `s3:ListAllMyBuckets`, `GetBucketLocation`, `ListBucket`, `DeleteBucket`, `GetObject`, `PutObject`, `DeleteObject`
- `sts:GetCallerIdentity`

</details>

## Deploy

```bash
make deploy
```

Or with a different model:

```bash
make deploy MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

Expect **10-15 minutes** on first run (~5 minutes on subsequent runs). The script is **idempotent** — you can run it repeatedly to push code changes without creating duplicate resources:

- **Gateway + Cognito**: created once, reused on subsequent deploys
- **Runtime container**: rebuilt and updated every run (picks up changes to `onboarding_app.py`, system prompt, etc.)
- **Lambda**: code updated every run (picks up changes to `hr_tools.py`, `mock_data.py`)
- **MCP target**: re-registered every run

What the script does on first deploy:

1. Creates a Python virtualenv at `src/.venv/` and installs dependencies
2. Deploys an AgentCore Gateway with a Cognito user pool + OAuth2 app client
3. Configures and deploys an AgentCore Runtime (builds via AWS CodeBuild)
4. Creates a Lambda + IAM role for the HR tools MCP backend
5. Registers the Lambda as an MCP target on the gateway
6. Injects gateway URL and Cognito credentials into the container via `agentcore deploy --env`
7. Tags every resource with `Sample=sample-amazon-bedrock-agentcore-employee-onboarding`
8. Writes `.env` with the credentials needed to invoke the runtime locally

If the script fails partway through, run `make clean` before retrying.

The model ID is written to `.env` as `MODEL_ID`. You can also edit `.env` and redeploy.

## Test the Deployment

```bash
# Check agent status
agentcore status

# Smoke test with curl (fastest)
make smoke-test

# CLI with formatted output
make cli

# Custom prompt
make cli PROMPT="onboard jane doe as software engineer"
```

## Configuration

### Generated Files

`deploy.sh` generates two configuration files:

- **`.env`** — OAuth2 credentials, gateway URL, feature flags. Used by the CLI for local invocation.
- **`.bedrock_agentcore.yaml`** — Agent configuration with runtime ARN and JWT authorizer. Used by the `agentcore` CLI.

See [`.env.example`](.env.example) for the full variable list.

### OAuth2 Authentication Flow

The sample uses a single Cognito user pool with client-credentials flow:

1. **Client → Cognito**: Exchange `client_id` + `client_secret` for an access token (scope: `[gateway-name]/invoke`)
2. **Client → Runtime**: Send the access token as a Bearer header with the invocation POST
3. **Runtime → Gateway**: The agent fetches its own Cognito token (injected via `--env` at deploy time) to authenticate MCP tool calls

### Manual Configuration

If automatic extraction fails, update `.env` manually:

```bash
AWS_REGION=us-east-1
AGENTCORE_MCP_URL=https://[gateway-id].gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
RUNTIME_CLIENT_ID=[client-id]
RUNTIME_CLIENT_SECRET=[client-secret]
RUNTIME_TOKEN_ENDPOINT=https://[cognito-domain].auth.us-east-1.amazoncognito.com/oauth2/token
RUNTIME_SCOPE=[gateway-name]/invoke
AGENT_USE_HR_TOOLS=true
```

> `RUNTIME_SCOPE` must match `[gateway-name]/invoke` exactly. Copy from the deployment output.

## Resource Cleanup

```bash
make clean
make verify-clean
```

Cleanup identifies resources via the `Sample=sample-amazon-bedrock-agentcore-employee-onboarding` tag, the `/bedrock-employee-onboarding/` IAM path, and exact agent-name matches.

**Removed:** AgentCore runtime + gateway, Cognito user pool, Lambda + IAM role, ECR repository, CodeBuild project, CloudWatch log group, tagged S3 buckets, local `.env` and `.bedrock_agentcore.yaml`.

**Deliberately not removed** (shared across all AgentCore deployments in the account):
- S3 bucket `bedrock-agentcore-codebuild-sources-<account>-<region>`
- Service-linked role `AWSServiceRoleForBedrockAgentCoreRuntimeIdentity`

See [SECURITY.md](SECURITY.md) for why these are excluded and how to remove them manually.

## Cost

**Rough estimate: $0.20–$0.60 for a 30-minute exploration** (one deploy, 5-10 invocations, then cleanup).

**Per-usage:**
- Amazon Bedrock model invocations (Claude Haiku 4.5) — dominant cost
- AWS Lambda invocations for HR tools
- AgentCore Runtime (per invocation) and Gateway (per request)
- CodeBuild minutes (one-time, ~5-8 min per deploy)

**Per-time (while resources exist):**
- ECR image storage (~200 MB)
- S3 build sources
- AgentCore Memory (STM, 30-day retention)
- CloudWatch Logs + X-Ray traces

**Effectively free:** Cognito user pool (under free tier), IAM roles.

Run `make clean` when done to stop ongoing charges.

**Pricing references:** [Bedrock](https://aws.amazon.com/bedrock/pricing/) · [AgentCore](https://aws.amazon.com/bedrock/agentcore/pricing/) · [Lambda](https://aws.amazon.com/lambda/pricing/) · [CodeBuild](https://aws.amazon.com/codebuild/pricing/)

## Monitoring

- **CloudWatch Logs**: `/aws/bedrock-agentcore/runtimes/[agent-id]-DEFAULT`
- **GenAI Observability**: CloudWatch → GenAI Observability → Agent Core dashboard
- **X-Ray**: Request tracing for latency and error analysis

## Debugging Tips

- **Missing env vars**: Run `python -c "import os; print(os.getenv('AGENTCORE_MCP_URL'))"` to confirm `.env` loaded.
- **OAuth failures**: Check that `RUNTIME_SCOPE` matches `[gateway-name]/invoke` and your system clock is correct.
- **Tool issues**: Set `AGENT_USE_HR_TOOLS=false` in `.env` to confirm the agent works without tools, then re-enable to isolate tool failures.
- **Raw transcript**: Use `make cli PROMPT="<prompt>" -- --debug` or `python src/cli/onboarding_cli.py "<prompt>" --debug` to see the unparsed SSE stream.

For detailed error-by-error solutions, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
