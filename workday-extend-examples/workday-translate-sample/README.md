# Workday Translate Sample - AWS AI Integration

An AWS Lambda function that provides real-time translation services using AWS Translate and Comprehend. This example demonstrates how to integrate Workday Extend with AWS AI/ML services to enable multi-language support for global workforces.

## Overview

This example demonstrates:
- Integration with AWS Translate for text translation
- Automatic language detection using AWS Comprehend
- Support for multiple language pairs
- Production-ready error handling and logging
- Serverless deployment using AWS SAM

## Architecture

```
Workday Orchestration → AWS Lambda → AWS Translate/Comprehend → Translated Response
```

The Lambda function:
1. Receives text and language parameters from Workday
2. Optionally detects source language using AWS Comprehend
3. Translates text using AWS Translate
4. Returns translated text in JSON response

## What's Included

- `src/index.py` - Python Lambda handler with translation logic
- `template.yaml` - AWS SAM template with Workday-specific configurations
- `samconfig.toml` - SAM deployment configuration (requires customization)
- `events/test-event.json` - Sample test event for local testing
- `test/payload.json` - Additional test payload
- `WORKDAY_DEPLOYMENT_GUIDE.md` - Comprehensive deployment instructions

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

### AWS Service Access
This example requires access to:
- AWS Lambda
- AWS Translate
- AWS Comprehend

## Quick Start

### 1. Configure Deployment Settings

Edit `samconfig.toml` with your Workday tenant information:
```toml
stack_name = "app-translate-example"  # Must have "app-" prefix
region = "us-west-2"                  # Your tenant region
s3_bucket = "workday-wcp-<org-short-id>-us-west-2"  # Your org ID and region
```

### 2. Deploy to AWS

```bash
cd sam-version
sam build && sam deploy
```

### 3. Configure Workday Extend

Follow the detailed instructions in [WORKDAY_DEPLOYMENT_GUIDE.md](WORKDAY_DEPLOYMENT_GUIDE.md) to:
- Create a Workday Extend app
- Build a translation orchestration
- Configure the Lambda invocation
- Test the integration

## API Reference

### Request Format
```json
{
  "text": "Hello world, this is a test translation",
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

### Response Format
```json
{
  "statusCode": 200,
  "body": "{\"translatedText\": \"Hola mundo, esta es una traducción de prueba\", \"sourceLanguage\": \"en\", \"targetLanguage\": \"es\"}"
}
```

### Parameters
- `text` (string, required): Text to translate
- `sourceLanguage` (string, optional): Source language code (e.g., "en", "es", "fr"). If omitted, language is auto-detected
- `targetLanguage` (string, required): Target language code

### Supported Languages

AWS Translate supports 75+ languages. Common language codes:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `ja` - Japanese
- `zh` - Chinese (Simplified)
- `pt` - Portuguese
- `ar` - Arabic

[Full list of supported languages](https://docs.aws.amazon.com/translate/latest/dg/what-is-languages.html)

## Testing

### Local Testing
```bash
sam local invoke TranslateFunction --event events/test-event.json
```

### AWS Testing
```bash
aws lambda invoke \
  --function-name WorkdayTranslateFunction \
  --payload file://test/payload.json \
  --region us-west-2 \
  output.json

cat output.json
```

## Deployment Guide

For complete step-by-step deployment instructions, including:
- AWS CLI and SAM CLI installation
- Workday tenant credential configuration
- IAM permissions and VPC setup
- Workday Extend orchestration creation
- Testing and troubleshooting

**See**: [WORKDAY_DEPLOYMENT_GUIDE.md](WORKDAY_DEPLOYMENT_GUIDE.md)

## Use Cases

This translation service can be used for:

- **Global Workforce Communication**: Translate messages, announcements, and documents for international teams
- **Multi-language Support**: Provide real-time translation in Workday custom applications
- **Document Translation**: Translate job descriptions, policies, and training materials
- **Customer Service**: Enable support teams to communicate across language barriers
- **Compliance**: Translate legal and compliance documents for regional requirements

## Features

- **Automatic Language Detection**: Optionally detect source language using AWS Comprehend
- **75+ Languages**: Support for major world languages through AWS Translate
- **High Quality**: Neural machine translation for natural-sounding results
- **Scalable**: Serverless architecture handles varying translation volumes
- **Cost-Effective**: Pay only for characters translated
- **Fast**: Low-latency responses suitable for real-time applications

## Extending This Example

Consider enhancing this example with:

- **Batch Translation**: Process multiple texts in a single request
- **Custom Terminology**: Use AWS Translate custom terminology for domain-specific terms
- **Translation Memory**: Store translations in DynamoDB to reduce costs and improve consistency
- **Format Preservation**: Handle HTML or formatted text translation
- **Quality Metrics**: Track translation quality and usage patterns
- **Caching**: Implement caching for frequently translated phrases

## Architecture Considerations

### Security
- Lambda runs in Workday-managed VPC
- Uses Workday-provided IAM execution role
- Credentials managed through AWS Systems Manager Parameter Store
- No sensitive data stored in function code

### Performance
- Cold start: ~1-2 seconds
- Warm execution: ~200-500ms
- Scales automatically based on demand
- No infrastructure management required

### Cost
- Lambda: Pay per invocation and execution time
- AWS Translate: Pay per character translated
- AWS Comprehend: Pay per language detection request (if used)
- Typical cost: $0.000001 per character for translation

## Troubleshooting

Common issues and solutions:

- **Translation errors**: Verify language codes are valid and supported by AWS Translate
- **Permission denied**: Ensure Lambda has `translate:TranslateText` and `comprehend:DetectDominantLanguage` permissions
- **Timeout errors**: Check VPC configuration and network connectivity
- **Invalid JSON**: Verify payload includes required `text` and `targetLanguage` fields
- **Character limit exceeded**: AWS Translate has a 10,000 byte limit per request

## Related Examples

- [Lambda Sum Sample](../lambda-sum-sample/) - Simpler example demonstrating basic integration pattern

## Resources

- [AWS Translate Documentation](https://docs.aws.amazon.com/translate/)
- [AWS Comprehend Documentation](https://docs.aws.amazon.com/comprehend/)
- [Workday Extend Documentation](https://developer.workday.com/documentation/extend)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## License

This example is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file for details.

## Contributing

We welcome improvements and additional features! Please see the repository [CONTRIBUTING](../../CONTRIBUTING.md) guide for details.
