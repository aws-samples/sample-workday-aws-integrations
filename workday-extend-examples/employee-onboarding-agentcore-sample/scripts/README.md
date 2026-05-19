# Scripts Directory

This directory contains all the automation scripts for the Amazon Bedrock HR Agent Demo.

## 📁 Script Overview

### Deployment Scripts
- **`deploy.sh`** - Complete automated deployment (Gateway + Runtime + OAuth2)

### Cleanup Scripts
- **`complete_cleanup.sh`** - ⭐ **Comprehensive cleanup** (removes ALL AgentCore resources)
- **`verify_cleanup.py`** - Verifies all resources have been cleaned up

### Testing Scripts
- **`test_agentcore_curl.sh`** - Smoke-test the deployed runtime with `curl` using values from `.env`
- **`../src/cli/onboarding_cli.py`** - CLI interface for testing the agent

## 🚀 Quick Commands

All scripts are wrapped by the root `Makefile`. Prefer `make` targets over calling scripts directly:

```bash
make deploy          # Fresh deployment
make smoke-test      # curl-based smoke test
make cli             # CLI with formatted output
make test            # Run the test suite
make clean           # Remove all AWS resources
make verify-clean    # Verify cleanup was successful
```

Run `make help` to see all available targets.

### Direct Script Invocation

If you need to call scripts directly (e.g., to pass flags not exposed by the Makefile):

```bash
./scripts/deploy.sh --model us.anthropic.claude-sonnet-4-5-20250929-v1:0
./scripts/test_agentcore_curl.sh "custom prompt here"
```

## 🧹 Cleanup Process

The `complete_cleanup.sh` script provides comprehensive cleanup of all AgentCore resources:

| Feature | Status |
|---------|--------|
| **Cognito User Pools** | ✅ Full cleanup with domains |
| **ECR Repositories** | ✅ Force deletion |
| **CodeBuild Projects** | ✅ Complete removal |
| **CloudWatch Logs** | ✅ All log groups |
| **IAM Roles & Policies** | ✅ Detach policies first |
| **S3 Buckets** | ✅ Cross-region (us-east-1 & us-west-2) |
| **Custom IAM Policies** | ✅ Detach and delete |
| **Error Handling** | ✅ Comprehensive |
| **Verification** | ✅ Built-in checks |

## 🔍 Verification Process

The `verify_cleanup.py` script checks:

1. **AWS Resources**:
   - Cognito User Pools
   - ECR Repositories  
   - CodeBuild Projects
   - CloudWatch Log Groups
   - IAM Roles and Policies
   - S3 Buckets (all regions)
   - Lambda Functions

2. **Local Files**:
   - `.env` configuration
   - `.bedrock_agentcore.yaml` agent config

3. **Exit Codes**:
   - `0` = All clean ✅
   - `1` = Issues found ❌

## 🛠️ Script Permissions

The Makefile runs `chmod +x` automatically. If calling scripts directly:
```bash
chmod +x scripts/deploy.sh scripts/complete_cleanup.sh
```

## 📋 Prerequisites

All scripts require:
- AWS CLI configured with appropriate permissions
- Python 3.10+ with boto3
- AWS region set to `us-east-1`

## 🔧 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x scripts/script_name.sh
   ```

2. **AWS Region Mismatch**
   ```bash
   aws configure set region us-east-1
   ```

3. **Python Command Not Found**
   ```bash
   make verify-clean
   ```

4. **Incomplete Cleanup**
   ```bash
   make clean
   ```

### Manual Cleanup

If scripts fail, see the main [README](../README.md#-cleanup) for manual cleanup guidance and [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for targeted fixes.

## 📖 Documentation

- **[README.md](../README.md)** - Main project documentation
- **[DEPLOYMENT.md](../DEPLOYMENT.md)** - Detailed deployment guide
- **[TROUBLESHOOTING.md](../TROUBLESHOOTING.md)** - Known issues and fixes
