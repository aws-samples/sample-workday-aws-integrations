# Lambda Sum Sample - Workday Extend Integration

A simple AWS Lambda function that demonstrates the fundamental pattern for integrating Workday Extend with AWS services. This example performs basic addition of two numbers, showcasing the request-response pattern between Workday orchestrations and AWS Lambda.

## Overview

This example demonstrates:
- Deploying a Python Lambda function using AWS SAM
- Configuring Workday Extend external endpoints
- Creating Workday orchestrations that invoke AWS Lambda
- Handling JSON request/response patterns
- Testing and validating the integration

## Architecture

```
Workday Orchestration → AWS Lambda (Sum Function) → Response
```

The Lambda function:
1. Receives a JSON payload with two numbers (`a` and `b`)
2. Performs addition
3. Returns the result in a JSON response

## What's Included

- `lambda_function.py` - Python Lambda handler that performs the sum operation
- `template.yaml` - AWS SAM template with Workday-specific configurations
- `samconfig.toml` - SAM deployment configuration (requires customization)
- `requirements.txt` - Python dependencies
- `SUM_DEPLOYMENT_GUIDE.md` - Comprehensive deployment instructions

## Prerequisites

### AWS Tools
- AWS CLI installed and configured
- SAM CLI installed
- Docker Desktop (for SAM builds)
- Python 3.11+

### Workday Access
- Workday Developer account
- Development tenant access
- Permissions to create Extend apps and orchestrations

## Quick Start

### 1. Configure Deployment Settings

Edit `samconfig.toml` with your Workday tenant information:
```toml
stack_name = "app-sum-example"  # Must have "app-" prefix
region = "us-west-2"            # Your tenant region
s3_bucket = "workday-wcp-<org-short-id>-us-west-2"  # Your org ID and region
```

### 2. Deploy to AWS

```bash
cd sam-version
sam build && sam deploy
```

### 3. Configure Workday Extend

Follow the detailed instructions in [SUM_DEPLOYMENT_GUIDE.md](SUM_DEPLOYMENT_GUIDE.md) to:
- Create a Workday Extend app
- Build an orchestration
- Configure the Lambda invocation
- Test the integration

## API Reference

### Request Format
```json
{
  "a": 10,
  "b": 20
}
```

### Response Format
```json
{
  "statusCode": 200,
  "body": "{\"a\": 10, \"b\": 20, \"result\": 30}"
}
```

### Parameters
- `a` (number, required): First number to add
- `b` (number, required): Second number to add

## Testing

### Local Testing
```bash
echo '{"a": 10, "b": 20}' > test-payload.json
sam local invoke SumLambdaFunction --event test-payload.json
```

### AWS Testing
```bash
aws lambda invoke \
  --function-name SumLambdaFunction \
  --payload file://test-payload.json \
  --region us-west-2 \
  output.json

cat output.json
```

## Deployment Guide

For complete step-by-step deployment instructions, including:
- AWS CLI and SAM CLI installation
- Workday tenant credential configuration
- Workday Extend orchestration setup
- Troubleshooting tips

**See**: [SUM_DEPLOYMENT_GUIDE.md](SUM_DEPLOYMENT_GUIDE.md)

## Use Cases

This pattern can be adapted for:
- Custom business calculations
- Data validation services
- Simple data transformations
- Integration testing and proof-of-concept
- Learning the Workday-AWS integration pattern

## Extending This Example

Consider enhancing this example with:
- Input validation and error handling
- Support for additional mathematical operations
- Integration with DynamoDB for calculation history
- CloudWatch metrics for monitoring usage
- API Gateway for REST API access

## Troubleshooting

Common issues and solutions:

- **Lambda not found**: Verify function name matches exactly in both SAM template and Workday orchestration
- **Permission errors**: Ensure Lambda is deployed with Workday-managed IAM role
- **Timeout errors**: Check VPC and region configuration
- **Invalid JSON**: Verify payload includes both `a` and `b` parameters

## Related Examples

- [Workday Translate Sample](../workday-translate-sample/) - More complex example using AWS AI services

## Resources

- [Workday Extend Documentation](https://developer.workday.com/documentation/extend)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)

## License

This example is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file for details.
