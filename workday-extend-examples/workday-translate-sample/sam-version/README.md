# Workday Extend AWS Translate Sample (SAM Version)

AWS Lambda function for text translation using AWS Translate, deployable via SAM.

## Prerequisites

- AWS CLI installed and configured
- SAM CLI installed (`pip install aws-sam-cli`)
- Python 3.11+

## Deploy

```bash
sam build
sam deploy --guided
```

On first deployment, SAM will prompt for:
- Stack name (e.g., `workday-translate-stack`)
- AWS region
- Confirm changes before deploy: Y
- Allow SAM to create IAM roles: Y
- Save parameters to samconfig.toml: Y

## Usage

The Lambda function accepts JSON input:

```json
{
  "text": "Hello world",
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

Response:
```json
{
  "translatedText": "Hola mundo",
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

## Test Locally

```bash
sam local invoke TranslateFunction -e events/test-event.json
```

## Parameters

- `text` (required): Text to translate
- `sourceLanguage` (optional): Source language code (defaults to 'auto')
- `targetLanguage` (optional): Target language code (defaults to 'en')

## Workday Extend Integration

Use the Function ARN from the deployment outputs to configure your Workday Extend external endpoint.
