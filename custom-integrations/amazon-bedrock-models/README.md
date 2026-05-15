# AI gateway for Amazon Bedrock

This directory provides guidance for deploying an AI gateway for Amazon Bedrock using Amazon API Gateway.

## Reference Implementation

The full AI gateway solution, including CloudFormation templates and deployment instructions, is available in the following repository:

**[Sample AI Gateway for Amazon Bedrock](https://github.com/aws-samples/sample-ai-gateway-for-amazon-bedrock)**

This solution deploys an Amazon API Gateway that sits in front of Amazon Bedrock, allowing client applications to use any AWS SDK to access Bedrock capabilities while the gateway handles authorization and request signing.

### Key Components

| Component | Purpose |
|-----------|---------|
| Amazon Route 53 | Custom domain routing |
| Amazon API Gateway | Entry point for requests (authorization, throttling, lifecycle management) |
| AWS Lambda Authorizer | Token validation (e.g., JWT) |
| Lambda Integration | Forwards requests to Bedrock endpoints with SigV4 signing |

## Getting Started

1. Review the [AI Gateway repository](https://github.com/aws-samples/sample-ai-gateway-for-amazon-bedrock) and its accompanying blog post for deployment instructions.
2. Deploy the CloudFormation stack in your AWS account.

## Related Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [Sample Workday AWS Integrations](https://github.com/aws-samples/sample-workday-aws-integrations)



