# Workday AWS Integration Examples

This repository contains a collection of example projects demonstrating how to integrate Workday with AWS services. These examples showcase practical implementations of Workday Extend functionality combined with AWS cloud-native capabilities to create powerful, scalable solutions.

## Table of Contents

- [About this Repository](#about-this-repository)
- [Examples](#examples)
- [Getting Started](#getting-started)
- [Learning Resources](#learning-resources)
- [Contributing](#contributing)
- [License](#license)

## About this Repository

This repository is maintained by the AWS Business Applications team in collaboration with Workday. Our goal is to provide practical, production-ready examples that demonstrate how organizations can extend their Workday investments using AWS services.

These examples are designed for developers who want to:
- Build custom integrations between Workday and AWS
- Leverage Workday Extend with serverless AWS architectures
- Implement scalable, cost-effective solutions for common business scenarios
- Learn best practices for Workday-AWS integration patterns

Each example includes complete source code, deployment guides, and configuration templates to help you get started quickly.

## Examples

### Workday Extend Examples

| Example | Description | AWS Services | Workday Features |
|---------|-------------|--------------|------------------|
| [Lambda Sum Sample](workday-extend-examples/lambda-sum-sample/) | Simple calculation service demonstrating basic Workday Extend to AWS Lambda integration | Lambda, SAM | Orchestrations, External Endpoints |
| [Workday Translate Sample](workday-extend-examples/workday-translate-sample/) | Real-time translation service using AWS AI services | Lambda, Translate, Comprehend, SAM | Orchestrations, External Endpoints |
| [Employee Onboarding AgentCore Sample](workday-extend-examples/employee-onboarding-agentcore-sample/) | AI-powered employee onboarding assistant using Amazon Bedrock AgentCore with MCP tools and OAuth2 authentication | Bedrock AgentCore, Lambda, Cognito, CodeBuild | AgentCore Runtime, MCP Gateway |

### Custom Integrations

| Example | Description | AWS Services | Workday Features |
|---------|-------------|--------------|------------------|
| [Bedrock Agentflow Sample](custom-integrations/amazon-bedrock-models/agentflow-bedrock-sample/) | Pre-configured agentflow integrating Workday Extend with Amazon Bedrock (Claude Sonnet 4.6) for multimodal chat with built-in tools | Bedrock | Agentflows |
| [AI Gateway for Amazon Bedrock](custom-integrations/amazon-bedrock-models/) | Reference for deploying an API Gateway-based AI gateway in front of Amazon Bedrock | API Gateway, Lambda, Bedrock | External Endpoints |


## Getting Started

### Prerequisites

To work with these examples, you'll need:

1. **Workday Access**
   - Access to [Workday Developer site](https://developer.workday.com/)
   - Workday development tenant

2. **AWS Tools**
   - [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and configured
   - [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) for serverless deployments
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for local testing

3. **Development Environment**
   - Python 3.11+ (for Python-based examples)
   - Git for cloning the repository

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/aws-samples/sample-workday-aws-integrations.git
   cd sample-workday-aws-integrations
   ```

2. **Choose an example**
   Navigate to the example directory you want to explore:
   ```bash
   cd workday-extend-examples/lambda-sum-sample
   ```

3. **Follow the deployment guide**
   Each example includes a detailed deployment guide with step-by-step instructions.

## What is Workday Extend?

Workday Extend is a platform that enables organizations to build custom applications and integrations that seamlessly connect with Workday's core functionality. It provides:

- **External Endpoints**: Connect to external services and APIs through secure, configurable endpoints
- **Custom Objects**: Create custom data structures that integrate with Workday's data model
- **Business Processes**: Build workflows that trigger external actions or consume external data
- **Orchestrations**: Coordinate complex multi-step processes spanning Workday and external systems
- **Security**: Enterprise-grade authentication with OAuth 2.0 and Workday's security model

## Integration Patterns

These examples demonstrate common integration patterns:

1. **Synchronous Request-Response**: Call AWS services from Workday orchestrations and receive immediate results
2. **Serverless Architecture**: Use AWS Lambda for cost-effective, auto-scaling compute
3. **AI/ML Services**: Integrate AWS AI services like Translate, Comprehend, and Rekognition
4. **Data Processing**: Perform complex calculations or transformations using AWS compute
5. **External API Integration**: Connect Workday to third-party services through AWS

## Learning Resources

### Official Workday Resources
- [Workday Developer Portal](https://developer.workday.com/)
- [Workday Extend Documentation](https://developer.workday.com/documentation/extend)
- [Workday Community](https://community.workday.com/)

### Official AWS Resources
- [AWS Serverless Application Model (SAM)](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

### Related AWS Examples
- [AWS SAM Examples](https://github.com/aws-samples/serverless-patterns)
- [AWS Lambda Examples](https://github.com/awsdocs/aws-lambda-developer-guide/tree/main/sample-apps)

## Real-World Applications

These patterns can be applied to numerous business scenarios:

- **Document Processing**: OCR, document classification, and content extraction
- **Data Analytics**: Complex calculations, machine learning predictions, and data analysis
- **Translation Services**: Multi-language support for global workforces
- **Integration Services**: Connecting to third-party APIs and data transformation
- **Notification Services**: SMS, email, and push notifications through AWS SNS/SES
- **File Processing**: Image resizing, format conversion, and batch processing

## Contributing

We welcome contributions! Whether it's fixing bugs, improving documentation, or adding new examples, your input helps the community. Please see our [CONTRIBUTING](CONTRIBUTING.md) guide for details on:

- How to submit issues and feature requests
- Code contribution guidelines
- Example submission requirements
- Code of conduct

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information on reporting security issues.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.

## Support

These examples are provided as-is for educational and demonstration purposes. For production deployments:
- Review and adapt the code to meet your specific requirements
- Follow your organization's security and compliance guidelines
- Test thoroughly in non-production environments first

For questions or issues:
- Open an issue in this repository
- Consult the Workday Developer Community
- Contact your AWS Solutions Architect or Workday representative

---

**Maintained by**: AWS Business Applications Team in collaboration with Workday
