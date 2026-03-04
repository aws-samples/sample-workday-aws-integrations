# Workday Extend AWS Translate Sample - Deployment Guide

This guide provides step-by-step instructions for deploying the AWS Translate Lambda function to a Workday-managed AWS tenant account and integrating it with Workday Extend.

## Prerequisites

### AWS Prerequisites (Required Setup)

#### 1. Install AWS CLI
The AWS Command Line Interface is required for deploying to AWS.

**Windows:**
1. Download the AWS CLI MSI installer from [AWS CLI Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. Run the installer and follow the setup wizard
3. Verify installation: Open Command Prompt and run `aws --version`

**macOS:**
```bash
# Using Homebrew (recommended)
brew install awscli

# Or download installer from AWS
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify installation: `aws --version`

#### 2. Install SAM CLI
AWS SAM (Serverless Application Model) CLI is used for building and deploying serverless applications.

**Prerequisites for SAM CLI:**
- Docker Desktop (required for local testing)
- Python 3.8+ 

**Install Docker Desktop:**
1. Download from [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Install and start Docker Desktop
3. Verify: `docker --version`

**Install SAM CLI:**
```bash
# Using pip (recommended)
pip install aws-sam-cli

# Verify installation
sam --version
```

**Alternative Installation Methods:**
- **Windows**: Download MSI installer from [SAM CLI Installation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **macOS**: `brew install aws-sam-cli`
- **Linux**: Follow [Linux installation guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html#install-sam-cli-instructions)

#### 3. Python 3.11+ Installation
Required for the Lambda runtime.

**Check Current Version:**
```bash
python3 --version
```

**Installation:**
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **macOS**: `brew install python@3.11` or download from python.org
- **Linux**: Use your distribution's package manager (e.g., `sudo apt install python3.11`)

### Workday Prerequisites
- Access to Workday Developer site (https://developer.workday.com/)
- Existing Workday development tenant (see [Creating Development Tenants](https://developer.workday.com/documentation/wqd1574121373563/ConceptWCPDevelopmentTenants) if needed)

### Verification Commands
Run these commands to verify all prerequisites are installed:
```bash
aws --version          # Should show AWS CLI version
sam --version          # Should show SAM CLI version  
python3 --version      # Should show Python 3.11+
docker --version       # Should show Docker version
```

### Additional Resources
- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/)
- [SAM CLI Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)

## Part 1: Accessing Workday Tenant AWS Credentials

### Step 1: Log into Workday Developer Site
1. Navigate to https://developer.workday.com/
2. Log in with your Workday developer credentials

### Step 2: Authenticate to Development Tenant
1. At the top right corner of the screen, click on your Workday Account name
2. In the dropdown menu, click "Sign in to Tenant" under the Tenant section
3. In the popup window:
   - Ensure "Development" environment is selected
   - Click the dropdown to choose your tenant
   - Click "Connect to Tenant" button
4. In the separate login window that appears:
   - Enter your tenant username and password (likely different from developer site credentials)
   - Click "Sign In"
5. Verify authentication: You should now see your tenant name displayed under your Workday account name in the upper right

### Step 3: Access Third Party Integrations
1. Click the hamburger menu (☰) in the upper left of the developer site
2. Under the "Console" section, click "Third Party Integrations"
   - Note: This option only appears after tenant authentication

### Step 4: Generate AWS CLI Credentials
1. In the "Third Party Integrations" screen, click "Generate AWS CLI Token"
2. Copy the provided AWS credentials:
   - `aws_access_key_id`
   - `aws_secret_access_key` 
   - `aws_session_token`
3. Click "Copy Configuration" to copy to clipboard

### Step 5: Configure AWS CLI with Workday Credentials

The Workday Developer site provides AWS credentials in a format that's perfect for file-based configuration. This is the recommended approach.

#### Method 1: File-Based Configuration (Recommended)

**Step 5.1: Locate AWS Credentials Directory**
```bash
# Check if AWS directory exists
ls ~/.aws/

# If directory doesn't exist, create it
mkdir -p ~/.aws/
```

**Step 5.2: Create/Edit Credentials File**
The copied configuration from Workday Developer site is already in the correct format for the AWS credentials file.

```bash
# Edit the credentials file
nano ~/.aws/credentials
# Or use your preferred text editor: vim, code, etc.
```

**Step 5.3: Paste Workday Credentials**
Paste the copied configuration directly into the file. It should look like this format:
```ini
[default]
aws_access_key_id = ASIA...
aws_secret_access_key = abc123...
aws_session_token = IQoJb3JpZ2luX2VjEP...
```

**Step 5.4: Set Region Configuration**
Create or edit the AWS config file to set your region:
```bash
# Edit the config file
nano ~/.aws/config
```

Add your Workday tenant region:
```ini
[default]
region = us-west-2
output = json
```

**Step 5.5: Verify Configuration**
Test that your AWS CLI is properly configured:
```bash
# Check AWS identity (should show Workday-managed account info)
aws sts get-caller-identity

# Test basic AWS access
aws s3 ls
```

#### Method 2: Command Line Configuration (Alternative)
If you prefer using AWS CLI commands:
```bash
aws configure set aws_access_key_id ASIA...
aws configure set aws_secret_access_key abc123...
aws configure set aws_session_token IQoJb3JpZ2lu...
aws configure set region us-west-2
```

#### Important Notes
- **Temporary Credentials**: Workday provides temporary AWS credentials that expire
- **Re-authentication**: You'll need to regenerate credentials periodically when they expire
- **Security**: Never commit these credentials to version control
- **Profile Management**: You can use named profiles if working with multiple AWS accounts

#### Troubleshooting
**If you get permission errors:**
1. Verify you're authenticated to the correct Workday tenant
2. Regenerate AWS credentials from Workday Developer site
3. Ensure you're using the correct region for your tenant

**If credentials expire:**
1. Return to Workday Developer site → Third Party Integrations
2. Click "Generate AWS CLI Token" again
3. Update your `~/.aws/credentials` file with new values

---

## Part 2: Workday Extend SAM Requirements

### Required SAM Template Configuration

For Workday Extend integration, your SAM template must include specific configurations that integrate with Workday's managed AWS infrastructure.

#### 1. IAM Role Configuration
```yaml
Role: '{{resolve:ssm:/workday-extend-tenant-config/LambdaExecutionRole}}'
```
- Uses Workday-managed IAM role from SSM Parameter Store
- Pre-configured with necessary permissions for Workday Extend integration

#### 2. VPC Configuration
```yaml
VpcConfig:
  SecurityGroupIds:
    - '{{resolve:ssm:/workday-extend-tenant-config/LambdaSecurityGroup}}'
  SubnetIds:
    - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet1}}'
    - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet2}}'
```
- Lambda must be deployed within Workday's managed VPC
- Security groups and subnets are pre-configured in the Workday tenant
- Retrieved via SSM parameters for security and consistency

#### 3. Required IAM Policies
```yaml
Policies:
  - Statement:
    - Effect: Allow
      Action:
        - translate:TranslateText
        - comprehend:DetectDominantLanguage
      Resource: '*'
```
- Additional permissions specific to your Lambda's functionality
- Combined with the base Workday execution role

#### 4. Function Outputs
```yaml
Outputs:
  FunctionName:
    Description: Lambda function name for Workday Extend
    Value: !Ref TranslateFunction
  FunctionArn:
    Description: Lambda function ARN for Workday Extend
    Value: !GetAtt TranslateFunction.Arn
```
- Function ARN is required for configuring Workday Extend external endpoints

### Key Requirements Summary
- **SSM Parameter Integration**: All infrastructure references use Workday-managed SSM parameters
- **VPC Deployment**: Lambda must run within Workday's managed VPC
- **Managed IAM Role**: Use Workday-provided execution role as base
- **Function ARN Output**: Required for Workday Extend orchestration configuration

### Reference Documentation
For additional SAM examples and requirements, see: [Workday Extend SAM Documentation](https://developer.workday.com/documentation/GUID-807619f6-1b04-4a31-8f29-661aa92058d4-enHYPHENus?q=Extend%20SAM%20example)

## Part 3: Configuration and Deployment

### Step 1: Determine Workday Tenant Region
1. Refer to [Workday Tenant Regions Documentation](https://developer.workday.com/documentation/GUID-4c546bf6-25df-4372-aa2a-6e07bb7b1967-enHYPHENus) to identify your tenant's AWS region
2. Common regions include `us-west-2`, `us-east-1`, `eu-west-1`
3. Note your region for the configuration steps below

### Step 2: Get Organization Short ID
1. In the Workday Developer site, click the hamburger menu (☰)
2. Under "Console" section, select "Account"
3. Copy the "Organization Short ID" value
4. You'll need this for the S3 bucket configuration

### Step 3: Configure samconfig.toml
Update your `samconfig.toml` file with the following required settings:

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
1. Build and deploy using SAM:
```bash
sam build && sam deploy
```

2. The deployment will use your configured AWS credentials from Part 1
3. Note the Function ARN from the deployment outputs - you'll need this for Workday orchestration

### Step 5: Test the Deployment (Optional)
Test your deployed Lambda function using AWS CLI:

```bash
# Create test payload
echo '{"text": "Hello world", "sourceLanguage": "en", "targetLanguage": "es"}' > test-payload.json

# Invoke the function
aws lambda invoke \
  --function-name WorkdayTranslateFunction \
  --payload file://test-payload.json \
  --region us-west-2 \
  output.json

# View results
cat output.json
```

Expected response:
```json
{
  "statusCode": 200,
  "body": "{\"translatedText\": \"Hola mundo\", \"sourceLanguage\": \"en\", \"targetLanguage\": \"es\"}"
}
```

## Part 4: Building Workday Orchestration

After successfully deploying your Lambda function, you need to create a Workday orchestration to call it.

### Step 1: Create New Integration App
1. On the Workday Developer home screen, click "Create an Extend App"
2. In the popup, click "Start from scratch"
3. Enter app name: `AWS Translate Example` (or your preferred name)
4. Click "Create and Go to Overview"

### Step 2: Add Orchestration
1. On the App screen, click "Add Orchestration" under the "Orchestrations" section
2. On the Create Orchestration screen:
   - Click "Synchronous Orchestration"
   - Give the orchestration a name (e.g., "TranslateOrchestration")
   - Click "Done"

### Step 3: Add JSON Data Component
The orchestration builder will open. You'll create a test payload using a JSON component.

1. Click the "Components" icon on the far left side of the builder
2. Under "Data Operations" section, drag "Create JSON" component into the orchestration diagram where it says "Drop Component Here"
3. In the JSON component editor:
   - Name: `TranslationJSONInput`
   - Click "Generate Structure"
4. In the text box that appears, paste this sample JSON payload:

```json
{
  "text": "Hello world, this is a test translation",
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

5. Click "Generate Structure"
6. Click "Close" to return to the builder

### Step 4: Add AWS Lambda Invoke Component
1. In the "Components" list, under "Amazon Web Services (AWS)" category, drag "Invoke AWS Lambda Function" component AFTER the JSON component
2. Configure the Lambda component:
   - **Name**: `invokeTranslateFunction`
   - **Function Name**: `WorkdayTranslateFunction`
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

### Expected Results
The orchestration should successfully:
1. Create the JSON payload with your test translation request
2. Invoke your AWS Lambda function
3. Return the translated text from AWS Translate

**Sample Expected Output:**
```json
{
  "statusCode": 200,
  "body": "{\"translatedText\": \"Hola mundo, esta es una traducción de prueba\", \"sourceLanguage\": \"en\", \"targetLanguage\": \"es\"}"
}
```

### Troubleshooting
- **Lambda not found**: Verify the function name matches exactly: `WorkdayTranslateFunction`
- **Permission errors**: Ensure your Lambda was deployed with the correct Workday IAM role
- **Timeout errors**: Check that your Lambda is deployed in the correct VPC and region
- **Invalid JSON**: Verify the JSON payload format matches the expected Lambda input structure

### Next Steps
Once your orchestration is working, you can:
- Modify the JSON payload to test different languages
- Integrate with Workday business objects to translate real data
- Add error handling and validation logic
- Create more complex workflows that use the translation results
