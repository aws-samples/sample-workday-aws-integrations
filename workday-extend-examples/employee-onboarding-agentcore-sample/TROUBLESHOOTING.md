# Amazon Bedrock HR Agent - Troubleshooting Guide

## Common Issues and Solutions

### 1. OAuth2 Authentication Errors

#### Problem: "400 Client Error: Bad Request" for OAuth2 token
```
OAuth2 token error: 400 Client Error: Bad Request for url: https://agentcore-xxx.auth.us-east-1.amazoncognito.com/oauth2/token
```

**Root Cause**: Incorrect OAuth2 scope in `.env` file

**Solution**: 
1. Check the correct scope for your gateway:
```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id [USER_POOL_ID] \
  --client-id [CLIENT_ID] \
  --region us-east-1 \
  --query "UserPoolClient.AllowedOAuthScopes"
```

2. Update `.env` file with the correct scope:
```bash
RUNTIME_SCOPE=[gateway-name]/invoke  # NOT bedrock-agentcore:invoke
```

#### Problem: "cannot access local variable 'resp' where it is not associated with a value"
**Root Cause**: OAuth2 token request fails, causing undefined variable in client code
**Solution**: Fix the OAuth2 scope issue above

### 2. AgentCore CLI Command Errors

#### Problem: "No such option: --gateway-name"
```bash
Usage: agentcore create_mcp_gateway [OPTIONS]
Try 'agentcore create_mcp_gateway --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --gateway-name Did you mean --name?                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Root Cause**: Incorrect parameter name in CLI command
**Solution**: Use `--name` instead of `--gateway-name`:
```bash
agentcore create_mcp_gateway --name "gateway-name" --region us-east-1
```

#### Problem: "No such command 'destroy'"
**Root Cause**: AgentCore CLI doesn't have a `destroy` command
**Solution**: Use AWS CLI to delete resources directly or manual cleanup via console

### 3. Runtime Configuration Errors

#### Problem: "Parameter validation failed: Invalid number of parameters set for tagged union structure authorizerConfiguration"
```
Unknown parameter in authorizerConfiguration: "type", must be one of: customJWTAuthorizer
Unknown parameter in authorizerConfiguration: "oauth2", must be one of: customJWTAuthorizer
```

**Root Cause**: Incorrect OAuth2 configuration format
**Solution**: Use the correct JWT authorizer format:
```bash
JWT_CONFIG='{"customJWTAuthorizer": {"discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/[USER_POOL_ID]/.well-known/openid-configuration", "allowedClients": ["[CLIENT_ID]"]}}'
```

#### Problem: "❌ No requirements file specified and none found automatically"
**Root Cause**: AgentCore configure command can't find requirements.txt
**Solution**: Specify the requirements file explicitly:
```bash
agentcore configure --requirements-file "src/agentcore/requirements.txt"
```

### 4. Deployment Issues

#### Problem: Runtime stuck in "Deploying" state
**Root Cause**: Underlying resources (ECR, CodeBuild) were deleted but runtime still references them
**Solution**: 
1. Delete the stuck runtime via AWS Console
2. Redeploy with fresh configuration

#### Problem: "ConflictException" during deployment
**Root Cause**: Existing agent with same name
**Solution**: Use the `--auto-update-on-conflict` flag:
```bash
agentcore launch --agent "agent-name" --auto-update-on-conflict
```

### 5. Cognito User Pool Issues

#### Problem: "User pool cannot be deleted. It has a domain configured that should be deleted first"
**Root Cause**: Cognito domains must be deleted before user pools
**Solution**: Delete domain first, then wait before deleting pool:
```bash
aws cognito-idp delete-user-pool-domain --domain "domain-name" --region us-east-1
sleep 10
aws cognito-idp delete-user-pool --user-pool-id "pool-id" --region us-east-1
```

### 6. Environment and Configuration Issues

#### Problem: "AccessDeniedException: Authorization method mismatch" when using `agentcore invoke`
**Root Cause**: The runtime uses OAuth2 (`customJWTAuthorizer`), but `agentcore invoke` sends AWS SigV4 credentials by default — it doesn't perform the Cognito token exchange.
**Solution**: Use `make smoke-test` or `make cli` instead. These handle the OAuth2 client-credentials flow automatically. The `agentcore invoke` command shown in `agentcore status` output does not work with OAuth2-configured runtimes.

#### Problem: "AGENTCORE_MCP_URL is not set"
**Root Cause**: Missing or incorrect environment configuration
**Solution**: Ensure `.env` file exists and contains:
```bash
AGENTCORE_MCP_URL=https://[gateway-id].gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
```

#### Problem: "No MCP tools discovered"
**Root Cause**: Gateway authentication failure or no tools registered
**Solution**: 
1. Verify gateway credentials in `.env`
2. Confirm `AGENT_USE_HR_TOOLS=true` if you expect the bundled HR tools to load
3. Register MCP tool servers with the gateway

## Diagnostic Commands

### Check Deployment Status
```bash
# Agent status
agentcore status

# Gateway status (via AWS Console or CLI)
aws cognito-idp list-user-pools --max-results 50 --region us-east-1

# ECR repositories
aws ecr describe-repositories --region us-east-1 --query "repositories[?contains(repositoryName, 'onboarding')]"

# CodeBuild projects
aws codebuild list-projects --region us-east-1 --query "projects[?contains(@, 'onboarding')]"
```

### Test OAuth2 Authentication
```bash
# Get access token
CLIENT_CREDENTIALS=$(echo -n "$CLIENT_ID:$CLIENT_SECRET" | base64)
curl -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $CLIENT_CREDENTIALS" \
  -d "grant_type=client_credentials&scope=$OAUTH_SCOPE"
```

### View Logs
```bash
# Runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/[agent-id]-DEFAULT \
  --follow

# CodeBuild logs
aws logs describe-log-groups --region us-east-1 \
  --query "logGroups[?contains(logGroupName, 'codebuild')]"
```

### Validate Configuration Files
```bash
# Check .env file
cat .env | grep -E "(CLIENT_ID|CLIENT_SECRET|TOKEN_ENDPOINT|SCOPE)"

# Check AgentCore config
cat .bedrock_agentcore.yaml | grep -A 5 "authorizer_configuration"

# Validate JSON syntax
echo '{"customJWTAuthorizer": {...}}' | python3 -m json.tool
```

## Recovery Procedures

### Orphaned Resources from Multiple Deploys

If you ran `make deploy` multiple times without cleaning up in between, `make clean` will find most resources by tag. However, if earlier deploys failed before tagging completed, some resources may be orphaned. To find and remove them:

```bash
# List all AgentCore gateways (look for ones with "bedrock-employee-onboarding" in the name)
aws bedrock-agentcore-control list-gateways --region us-east-1

# Delete a specific orphaned gateway (delete targets first)
aws bedrock-agentcore-control list-gateway-targets --gateway-id <id> --region us-east-1
aws bedrock-agentcore-control delete-gateway-target --gateway-id <id> --target-id <tid> --region us-east-1
aws bedrock-agentcore-control delete-gateway --gateway-id <id> --region us-east-1

# List Cognito user pools (look for ones created by this sample)
aws cognito-idp list-user-pools --max-results 50 --region us-east-1

# Delete an orphaned Cognito pool (delete domain first)
aws cognito-idp describe-user-pool --user-pool-id <pool-id> --region us-east-1 --query "UserPool.Domain"
aws cognito-idp delete-user-pool-domain --domain <domain> --user-pool-id <pool-id> --region us-east-1
aws cognito-idp delete-user-pool --user-pool-id <pool-id> --region us-east-1

# List CloudWatch log groups for this agent
aws logs describe-log-groups --region us-east-1 \
  --query "logGroups[?contains(logGroupName, 'employee_onboarding')].logGroupName"
```

After manual cleanup, run `make verify-clean` to confirm everything is gone.

### Complete Cleanup and Redeploy
```bash
# 1. Run cleanup
make clean

# 2. Wait for resources to be fully deleted
sleep 60

# 3. Redeploy from scratch
make deploy
```

### Partial Recovery (Keep Gateway, Redeploy Runtime)
```bash
# 1. Delete only runtime
agentcore configure --name "employee_onboarding" --entrypoint "src/agentcore/onboarding_app.py"
agentcore launch --agent "employee_onboarding" --auto-update-on-conflict

# 2. Update .env with existing gateway credentials
```

### Manual Resource Cleanup
```bash
# ECR repositories
aws ecr delete-repository --repository-name "bedrock-agentcore-employee_onboarding" --region us-east-1 --force

# CodeBuild projects
aws codebuild delete-project --name "bedrock-agentcore-employee_onboarding-builder" --region us-east-1

# IAM roles
aws iam delete-role --role-name "AmazonBedrockAgentCoreSDKRuntime-us-east-1-[suffix]"
aws iam delete-role --role-name "AmazonBedrockAgentCoreSDKCodeBuild-us-east-1-[suffix]"

# CloudWatch log groups
aws logs delete-log-group --log-group-name "/aws/bedrock-agentcore/runtimes/[agent-id]-DEFAULT" --region us-east-1
```

## Prevention Best Practices

1. **Always use `make` targets** (`make deploy`, `make clean`) rather than manual commands
2. **Check prerequisites** before deployment (AWS CLI, credentials, region)
3. **Backup configurations** before making changes
4. **Test OAuth2 tokens** before invoking the agent
5. **Monitor CloudWatch logs** during deployment
6. **Use consistent naming** for resources
7. **Document custom configurations** for team members

## Getting Help

1. **Check CloudWatch logs** first for detailed error messages
2. **Use diagnostic commands** to validate configuration
3. **Compare with working examples** in documentation
4. **Test components individually** (OAuth2, gateway, runtime)
5. **Clean up and redeploy** if issues persist
