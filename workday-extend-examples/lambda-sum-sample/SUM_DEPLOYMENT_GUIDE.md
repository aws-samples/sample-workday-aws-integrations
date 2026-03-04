# AWS SAM Lambda Sum Sample – Deployment Guide

This guide provides step-by-step instructions for deploying the **Lambda Sum Function** to a Workday-managed AWS tenant account and integrating it with Workday Extend. The function takes two parameters (`a` and `b`) and returns their sum.

---

## Prerequisites

### AWS Prerequisites (Required Setup)

#### 1. Install AWS CLI
The AWS Command Line Interface is required for deploying to AWS.

**Windows:**
1. Download the AWS CLI MSI installer from [AWS CLI Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. Run the installer and follow the setup wizard
3. Verify installation: `aws --version`

**macOS:**
```bash
brew install awscli
# Or download installer
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify installation:
```bash
aws --version
```

---

#### 2. Install SAM CLI
AWS SAM (Serverless Application Model) CLI is used for building and deploying serverless applications.

**Prerequisites for SAM CLI:**
- Docker Desktop (required for local testing)
- Python 3.11+

**Install Docker Desktop:**
1. Download from [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Install and start Docker Desktop
3. Verify: `docker --version`

**Install SAM CLI:**
```bash
pip install aws-sam-cli
sam --version
```

Alternative Installation Methods:
- **Windows**: [Download MSI installer](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **macOS**: `brew install aws-sam-cli`
- **Linux**: [Linux installation guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html#install-sam-cli-instructions)

---

#### 3. Python 3.11+ Installation

Check Current Version:
```bash
python3 --version
```

Install if needed:
- **Windows**: [python.org](https://www.python.org/downloads/)
- **macOS**: `brew install python@3.11` or download installer
- **Linux**: Use your package manager (e.g., `sudo apt install python3.11`)

---

### Workday Prerequisites
- Access to [Workday Developer site](https://developer.workday.com/)
- Existing Workday development tenant

### Verification Commands
```bash
aws --version
sam --version
python3 --version
docker --version
```

---

## Part 1: Accessing Workday Tenant AWS Credentials

### Step 1: Log into Workday Developer Site
1. Navigate to https://developer.workday.com/
2. Log in with your Workday developer credentials

### Step 2: Authenticate to Development Tenant
1. Click your Workday Account name (top right)
2. Select "Sign in to Tenant"
3. Ensure "Development" environment is chosen
4. Authenticate with your tenant username/password

### Step 3: Access Third Party Integrations
- Click the hamburger menu (☰)
- Select **Third Party Integrations**

### Step 4: Generate AWS CLI Credentials
- Click "Generate AWS CLI Token"
- Copy `aws_access_key_id`, `aws_secret_access_key`, `aws_session_token`

### Step 5: Configure AWS CLI with Workday Credentials

**File-Based Configuration (Recommended):**
```bash
mkdir -p ~/.aws
nano ~/.aws/credentials
```

Paste credentials in this format:
```ini
[default]
aws_access_key_id = ASIA...
aws_secret_access_key = abc123...
aws_session_token = IQoJ...
```

Configure region in `~/.aws/config`:
```ini
[default]
region = us-west-2
output = json
```

Verify configuration:
```bash
aws sts get-caller-identity
aws s3 ls
```

---

## Part 2: Workday Extend SAM Requirements

Your SAM template must include Workday-specific configurations.

### 1. IAM Role Configuration
```yaml
Role: '{{resolve:ssm:/workday-extend-tenant-config/LambdaExecutionRole}}'
```

### 2. VPC Configuration
```yaml
VpcConfig:
  SecurityGroupIds:
    - '{{resolve:ssm:/workday-extend-tenant-config/LambdaSecurityGroup}}'
  SubnetIds:
    - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet1}}'
    - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet2}}'
```

### 3. Required IAM Policies
```yaml
Policies:
  - Statement:
    - Effect: Allow
      Action:
        - logs:CreateLogGroup
        - logs:CreateLogStream
        - logs:PutLogEvents
      Resource: '*'
```

### 4. Function Outputs
```yaml
Outputs:
  FunctionName:
    Description: Lambda function name for Workday Extend
    Value: !Ref SumLambdaFunction
  FunctionArn:
    Description: Lambda function ARN for Workday Extend
    Value: !GetAtt SumLambdaFunction.Arn
```

---

## Part 3: Configuration and Deployment

### Step 1: Determine Workday Tenant Region
Check [Tenant Regions Documentation](https://developer.workday.com/documentation/GUID-4c546bf6-25df-4372-aa2a-6e07bb7b1967-enHYPHENus).

### Step 2: Get Organization Short ID
1. In the Workday Developer site, click the hamburger menu (☰)
2. Under "Console" section, select "Account"
3. Copy the "Organization Short ID" value
4. You'll need this for the S3 bucket configuration

### Step 3: Configure `samconfig.toml`
```toml
[default.global.parameters]
stack_name = "app-YourStackName"  # Must have "app-" prefix
region = "us-west-2"              # Replace with your tenant region
s3_bucket = "workday-wcp-<org-short-id>-us-west-2"  # Replace <org-short-id> and region

[default.deploy.parameters]
resolve_s3 = false

[default.package.parameters]
resolve_s3 = false
```

**Critical Requirements:**
- **Stack Name**: Must include `app-` prefix
- **Region**: Must match your Workday tenant region
- **S3 Bucket**: Format is `workday-wcp-<org-short-id>-<region>`
- **resolve_s3**: Must be set to `false` for both deploy and package

**⚠️ Important**: Replace the placeholder values with YOUR specific:
- Organization Short ID
- Tenant region
- Do NOT use the example values from the sample code

### Step 4: Deploy the Stack
```bash
sam build && sam deploy
```

### Step 5: Test the Deployment
```bash
echo '{"a": 10, "b": 20}' > test-payload.json

aws lambda invoke   --function-name SumLambdaFunction   --payload file://test-payload.json   --region us-west-2   output.json

cat output.json
```

Expected response:
```json
{
  "statusCode": 200,
  "body": "{\"a\": 10, \"b\": 20, \"result\": 30}"
}
```

---

## Part 4: Building Workday Orchestration

### Step 1: Create New Integration App
1. On the Workday Developer home screen, click "Create an Extend App"
2. In the popup, click "Start from scratch"
3. Enter app name: `AWS Sum Example` (or your preferred name)
4. Click "Create and Go to Overview"

### Step 2: Add Orchestration
1. On the App screen, click "Add Orchestration" under the "Orchestrations" section
2. On the Create Orchestration screen:
   - Click "Synchronous Orchestration"
   - Give the orchestration a name (e.g., "SumOrchestration")
   - Click "Done"

### Step 3: Add JSON Data Component
The orchestration builder will open. You'll create a test payload using a JSON component.

1. Click the "Components" icon on the far left side of the builder
2. Under "Data Operations" section, drag "Create JSON" component into the orchestration diagram where it says "Drop Component Here"
3. In the JSON component editor:
   - Name: `LambdaSumJSONInput`
   - Click "Generate Structure"
4. In the text box that appears, paste this sample JSON payload:
```json
{
  "a": 15,
  "b": 5
}
```
5. Click "Generate Structure"
6. Click "Close" to return to the builder

### Step 4: Add AWS Lambda Invoke Component
1. In the "Components" list, under "Amazon Web Services (AWS)" category, drag "Invoke AWS Lambda Function" component AFTER the JSON component
2. Configure the Lambda component:
   - **Name**: `invokeSumFunction`
   - **Function Name**: `SumLambdaFunction`
   - **Payload**: Click the "+" button
     - Select "Data from Orchestration Steps" > "Create JSON" > "data"
     - This connects the JSON output to the Lambda input
   - Click "Close"

### Step 5: Save and Deploy
1. In the top right of the builder, click "Save All to App Hub"
2. Wait for the blue button next to "Save All" to finish building
3. Once complete, click the "Built" button
4. In the dropdown that appears, click "Deploy"
5. Wait for deployment to complete

### Step 6: Test the Orchestration

1. After deployment, a black arrow icon will appear on the right
2. Click the arrow to run a test
3. Select "application/json" for the content type
4. When prompted for initial payload, enter: `{}`
   - Note: The real payload is set in the JSON component, but the interface requires an input
5. Execute the test by clicking the "Run Orchestration" button

Expected results:
```json
{
  "statusCode": 200,
  "body": "{\"a\": 15, \"b\": 5, \"result\": 20}"
}
```

---

## Troubleshooting

- **Lambda not found**: Verify the function name.  
- **Permission errors**: Ensure correct IAM role is used.  
- **Timeout errors**: Check VPC/region settings.  
- **Invalid JSON**: Ensure payload matches schema (`a` and `b` required).  

---

