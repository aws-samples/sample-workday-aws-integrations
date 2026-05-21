# Getting Started with Workday Extend and AWS Lambda: Your First Cloud-Native Integration

*By Anthony McClure, Alicia Bane, Fritz Lam, and Gene Krevets*

## Introduction

Organizations running Workday rely on it as the system of record for HR, finance, and planning. Yet business processes rarely live within a single platform. A compensation calculation needs external market data. A hiring workflow triggers provisioning in downstream systems. A compliance check requires real-time validation against a third-party service.

Workday Extend solves this by allowing organizations to build custom integrations that connect Workday's core functionality with external services through secure endpoints, orchestrations, and custom objects. The question becomes: where should those external services run?

AWS Lambda provides a natural answer. It is serverless, scales to zero when idle, runs within Workday-managed VPCs for security, and deploys through infrastructure as code for repeatability. The combination of Workday Extend and AWS Lambda enables organizations to push compute-intensive or integration-heavy logic outside Workday while maintaining the security, compliance, and user experience standards Workday is known for.

This post walks through a complete, working example: a simple Lambda function invoked by a Workday Orchestration. The function performs addition of two numbers. The math is trivial by design. The integration pattern — Workday Orchestration calling an AWS Lambda function through a secure external endpoint — is the reusable foundation for every Workday-to-AWS integration you will build.

## Understanding Workday Extend

Workday Extend is Workday's platform for building custom applications and integrations that operate within Workday's security, compliance, and UX framework. Unlike traditional integration middleware that sits between systems, Extend allows developers to create extensions that behave as first-class Workday features from the end user's perspective.

Extend operates on five key primitives:

- **External Endpoints** — Secure, configurable connections to external services and APIs. Each endpoint defines the target URL, authentication mechanism (OAuth 2.0, API keys, or mutual TLS), and request/response schemas. Endpoints are registered centrally and reusable across multiple orchestrations.

- **Orchestrations** — Multi-step workflows that coordinate actions across Workday and external systems. Orchestrations support sequential processing, conditional branching, parallel execution, error handling with retry logic, and data transformation between steps. They are the "glue" that connects Workday business events to external compute.

- **Custom Objects** — Data structures you define that integrate with Workday's existing data model. Custom objects can store results from external calls, hold intermediate state, or extend Workday's native entities with additional attributes.

- **Business Processes** — Workflows that trigger orchestrations based on Workday events (a new hire, a compensation change, a purchase requisition). Business processes provide the event-driven entry point that kicks off your integration.

- **Security** — All Extend components inherit Workday's role-based access control. External endpoint credentials are stored in Workday's secrets management. Lambda functions execute within Workday-managed VPCs with no public internet access. OAuth 2.0 handles authentication between Workday and AWS.

The key insight is that Workday manages the AWS account and VPC where your Lambda functions deploy. You write the code; Workday handles the network isolation, IAM boundaries, and credential rotation. This is different from a typical "bring your own AWS account" pattern and simplifies the security posture for both the customer and the integration developer.

## The Integration Pattern

Every Workday Extend + AWS integration follows the same core architecture:

```
Workday Orchestration → External Endpoint → AWS Lambda → JSON Response → Workday
```

Three components make this work:

1. **AWS Lambda function** — Your custom logic deployed as a serverless function. It receives a JSON payload, processes it, and returns a JSON response. AWS SAM handles packaging and deployment.

2. **Workday Extend External Endpoint** — A secure, configurable connection point within Workday that knows how to reach your Lambda function. This endpoint defines the URL, authentication method, and request/response mapping.

3. **Workday Orchestration** — A workflow within Workday that coordinates the end-to-end process. It collects input data, calls the external endpoint, receives the response, and routes the result back into Workday objects or business processes.

The Lambda function runs inside a Workday-managed VPC with proper IAM controls. Credentials are managed through the Workday Developer site, which provides temporary AWS credentials scoped to the tenant's account. This means your code executes in an isolated, secured environment without you managing network infrastructure.

## Technical Walkthrough

### Prerequisites

Before building this integration, you need:

- **AWS tools**: AWS CLI, SAM CLI, Docker Desktop, Python 3.11+
- **Workday access**: Developer account and development tenant access with permissions to create Extend apps and orchestrations
- **Git**: To clone the sample repository

### Step 1: Clone and Review the Lambda Function

```bash
git clone https://github.com/aws-samples/sample-workday-aws-integrations.git
cd sample-workday-aws-integrations/workday-extend-examples/lambda-sum-sample/sam-version
```

The Lambda handler (`lambda_function.py`) is straightforward Python:

```python
import json

def lambda_handler(event, context):
    """
    Lambda takes two parameters and returns a simple calculation.
    Expected input like:
    {
        "a": 5,
        "b": 3
    }
    """
    try:
        a = event.get("a")
        b = event.get("b")
        
        if a is None or b is None:
            return {
                "statusCode": 400,
                "body": json.dumps("Error: 'a' and 'b' must be provided")
            }
        
        result = a + b  # simple sum calculation

        return {
            "statusCode": 200,
            "body": json.dumps({
                "a": a,
                "b": b,
                "result": result
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(str(e))
        }
```

The function accepts two numbers (`a` and `b`), validates they are present, computes their sum, and returns the result as JSON. It includes input validation (400 for missing parameters) and a top-level exception handler (500 for unexpected errors). Replace this logic with any computation your business requires: tax calculations, address validation, credit scoring, or data enrichment from external APIs.

### Step 2: Review the SAM Template

The `template.yaml` defines the infrastructure as code for the Lambda function:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Lambda function that sums two numbers.

Globals:
  Function:
    Timeout: 3
    Runtime: python3.11

Resources:
  SumLambdaFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Role: '{{resolve:ssm:/workday-extend-tenant-config/LambdaExecutionRole}}'
      VpcConfig:
        SecurityGroupIds:
          - '{{resolve:ssm:/workday-extend-tenant-config/LambdaSecurityGroup}}'
        SubnetIds:
          - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet1}}'
          - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet2}}'
      Handler: lambda_function.lambda_handler
```

Several elements in this template are specific to the Workday Extend deployment model:

- **`Role`** — The IAM execution role is resolved at deploy time from AWS Systems Manager Parameter Store (`/workday-extend-tenant-config/LambdaExecutionRole`). Workday pre-provisions this role in the tenant's AWS account with the appropriate permissions boundary.

- **`VpcConfig`** — The Lambda function deploys into a Workday-managed VPC. The security group and subnet IDs are also stored in Parameter Store, pre-configured by Workday when the tenant is provisioned. This provides network isolation: the function can reach AWS services via VPC endpoints but has no public internet route by default.

- **`Runtime: python3.11`** and **`Timeout: 3`** — Python 3.11 is the supported runtime. The 3-second timeout is appropriate for simple calculations; increase it for functions that call downstream AWS services (Amazon Translate, Textract, etc.).

- **`CodeUri: ./`** — SAM packages everything in the current directory (your Lambda handler and any dependencies from `requirements.txt`) into the deployment artifact.

The `{{resolve:ssm:...}}` dynamic references mean you do not hard-code account-specific values in your template. The same template works across development, staging, and production tenants, with each tenant's Parameter Store holding its own infrastructure values.

### Step 3: Configure Deployment Settings

Edit `samconfig.toml` with your Workday tenant information:

```toml
stack_name = "app-sum-example"          # Must have "app-" prefix
region = "us-west-2"                     # Your tenant region
s3_bucket = "workday-wcp-<org-short-id>-us-west-2"  # Your org ID and region
```

The `app-` prefix is required for all CloudFormation stacks deployed within the Workday-managed AWS account (Workday uses this prefix to scope permissions and prevent naming collisions). The S3 bucket and region must match your Workday tenant configuration, available in the Workday Developer site under your organization's AWS settings.

### Step 4: Deploy to AWS

```bash
sam build && sam deploy
```

SAM packages your Lambda function, creates the necessary IAM roles, and deploys the CloudFormation stack. On completion, note the function name in the output — you will need it for the Workday configuration.

### Step 5: Test the Lambda Function

**Local testing** (before deploying):

```bash
echo '{"a": 10, "b": 20}' > test-payload.json
sam local invoke SumLambdaFunction --event test-payload.json
```

Expected output:
```json
{"statusCode": 200, "body": "{\"a\": 10, \"b\": 20, \"result\": 30}"}
```

**AWS testing** (after deployment):

```bash
aws lambda invoke \
  --function-name SumLambdaFunction \
  --payload file://test-payload.json \
  --region us-west-2 \
  output.json

cat output.json
```

### Step 6: Configure Workday Extend

With the Lambda function deployed and tested, configure the Workday side:

1. **Access Workday Tenant AWS Credentials** — Generate temporary AWS credentials from the Workday Developer site. These credentials are scoped to your tenant's AWS account and expire after a configurable period.

2. **Create a Workday Extend App** — In your development tenant, create a new Extend application. This serves as the container for your external endpoints and orchestrations.

3. **Define the External Endpoint** — Point it to your deployed Lambda function. Configure the request format (JSON with `a` and `b` fields) and expected response format (JSON with `statusCode` and `body` fields).

4. **Build an Orchestration** — Create a Workday Orchestration that:
   - Accepts input parameters (two numbers)
   - Calls your external endpoint with those parameters as JSON
   - Receives the JSON response
   - Parses the `body` field to extract the `result` value
   - Maps the result back into a Workday variable or custom object

5. **Test end-to-end** — Execute the orchestration from within Workday. Verify the response flows back correctly and appears in the expected location.

The [SUM_DEPLOYMENT_GUIDE.md](https://github.com/aws-samples/sample-workday-aws-integrations/blob/main/workday-extend-examples/lambda-sum-sample/SUM_DEPLOYMENT_GUIDE.md) in the repository provides step-by-step screenshots and configuration details for each Workday Extend component.

## How Orchestrations Work with AWS

Workday Orchestrations are the coordination layer that makes these integrations powerful beyond simple request-response:

- **Sequential processing** — Orchestrations call multiple AWS services in sequence, passing data between steps and maintaining state throughout the process. A single orchestration might validate input, call Lambda for a calculation, store the result in a custom object, and send a notification.

- **Conditional logic** — Based on responses from AWS services, orchestrations branch to different paths. A validation failure routes to an error handler; a successful result triggers the next step. This logic is configured declaratively in the Workday UI.

- **Error handling** — Built-in retry logic, fallback procedures, and error reporting ensure resilience. If your Lambda returns a 500 status code, the orchestration can retry with exponential backoff, route to an alternate path, or notify an administrator.

- **Data transformation** — Results from AWS services are transformed and mapped back into Workday objects. JSONPath-like expressions let you extract nested fields from Lambda responses and assign them to Workday variables or custom object fields.

This means your Lambda function only needs to handle one responsibility well. The orchestration handles the workflow coordination.

## Architecture Considerations

### Security

This integration deploys within Workday's security model:

- Lambda runs in a Workday-managed VPC with no public internet access by default
- IAM roles are scoped to the minimum permissions required, enforced by Workday's permissions boundary
- Credentials are temporary, generated through the Workday Developer site with configurable TTL
- No secrets are stored in function code or environment variables
- All parameters (role ARN, security groups, subnets) are dynamically resolved from Parameter Store

### Cost

Serverless architecture means you pay only for execution:

- **Lambda**: $0.20 per 1M requests + $0.0000166667 per GB-second of compute
- **At typical Workday volumes**: A function processing 10,000 orchestration calls per month with 128MB memory and 100ms average execution costs less than $0.05/month
- **No idle cost**: The function scales to zero when no orchestrations are running

### Observability

Every invocation is logged to AWS CloudWatch. Add structured logging in your Lambda function to trace requests from Workday through to your response:

```python
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Received request: {json.dumps(event)}")
    # ... processing ...
    logger.info(f"Returning result: {result}")
```

CloudWatch logs are accessible from the Workday Developer site's AWS console, scoped to your tenant. Use CloudWatch Insights to query across invocations and identify patterns in errors or latency.

## Extending This Pattern

This "sum" example establishes the pattern. The real power emerges when you replace the addition logic with business-critical operations:

| Use Case | Lambda Logic | AWS Services |
|---|---|---|
| Address validation | Geocode and verify addresses | Amazon Location Service |
| Document OCR | Extract text from uploaded documents | Amazon Textract |
| Translation | Translate HR communications | Amazon Translate, Comprehend |
| Fraud detection | Score transactions in real-time | Amazon SageMaker |
| Notifications | Send SMS/email confirmations | Amazon SNS, SES |
| Data enrichment | Pull market data or company info | Lambda + external APIs |
| AI assistance | Generate summaries or recommendations | Amazon Bedrock |

Each of these follows the identical pattern: Workday Orchestration → External Endpoint → Lambda → AWS Service → Response. The SAM template structure remains the same; you add IAM permissions for the additional AWS services to the execution role and increase the timeout as needed.

## Conclusion and Next Steps

You now have a working integration between Workday Extend and AWS Lambda. The pattern is intentionally simple: a serverless function deployed in a Workday-managed VPC, an external endpoint configured in Workday Extend, and an orchestration that ties them together. This foundation unlocks the full catalog of AWS services from within Workday workflows.

**To get started:**

1. Clone the [sample repository](https://github.com/aws-samples/sample-workday-aws-integrations) and deploy the Lambda Sum example to your Workday development tenant.
2. Follow the [SUM_DEPLOYMENT_GUIDE.md](https://github.com/aws-samples/sample-workday-aws-integrations/blob/main/workday-extend-examples/lambda-sum-sample/SUM_DEPLOYMENT_GUIDE.md) for step-by-step Workday Extend configuration with screenshots.
3. Verify the end-to-end flow works from Workday Orchestration through to Lambda response.
4. Replace the sum logic with your first real use case — data validation, an API call, or a calculation your team needs today.

For a more advanced example that integrates AWS AI/ML services with Workday Extend, see the next post in this series: *Real-Time Translation in Workday with AWS Translate and Comprehend*.


---

## Series Navigation

- **Part 1: Getting Started with Workday Extend and AWS Lambda** (this post)
- [Part 2: Real-Time Translation in Workday with AWS Translate and Comprehend](blog-02-real-time-translation.md)
- [Part 3: Building an AI Employee Onboarding Agent with Amazon Bedrock AgentCore](blog-03-ai-onboarding-agent.md)

---

The complete source code, SAM templates, and deployment guides are available in the [aws-samples/sample-workday-aws-integrations](https://github.com/aws-samples/sample-workday-aws-integrations/tree/main/workday-extend-examples) repository on GitHub.
