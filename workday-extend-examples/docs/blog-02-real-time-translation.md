# Real-Time Translation in Workday with AWS Translate and Comprehend

*By Anthony McClure, Alicia Bain, Fritz Lam, and Gene Krevets*

## Introduction

Global organizations manage workforces that span dozens of languages. An HR policy written in English needs to reach employees in Tokyo, São Paulo, and Berlin in their native languages. A manager in France submits a job description that recruiters in the US need to review. An employee in Mexico files a benefits question that a centralized support team needs to understand immediately.

Workday is where these workflows live, but Workday does not provide native real-time translation. Teams resort to manual translation services (slow and expensive), copy-pasting into external tools (insecure and disconnected from the workflow), or maintaining duplicate content in each language (error-prone and unmaintainable).

AWS Translate provides neural machine translation across 75+ languages with sub-second response times. AWS Comprehend adds automatic language detection, eliminating the need for users to specify what language they are writing in. By connecting these services to Workday through Workday Extend, organizations can deliver translation directly within existing workflows: a single orchestration call translates text on demand, automatically detects the source language, and returns results into Workday objects.

This post builds on the [foundational Workday Extend + Lambda pattern](blog-01-getting-started-with-lambda.md) from Part 1 of this series. If you have not deployed the Lambda Sum example, start there to understand the core integration pattern. This post adds two AWS AI services to the mix and shows how to handle optional parameters, auto-detection, and production-ready error handling.

## The Problem: Language Barriers in Enterprise HR

Consider these scenarios that organizations with global workforces encounter daily:

**Scenario 1: Policy rollout.** HR publishes a new parental leave policy. The company operates in 14 countries. Translating the document through a professional service takes 2 weeks and costs $3,000+ per language. By the time translations arrive, the policy has been revised twice.

**Scenario 2: Global hiring.** A hiring manager in Germany writes a job description in German. The talent acquisition team in the US needs an English version for the global careers page. The manager also wants to post in French for the Swiss office.

**Scenario 3: Employee support.** An employee in Brazil submits a benefits question in Portuguese through a Workday custom app. The benefits team in Chicago needs to read the question, draft a response, and have it translated back to Portuguese.

In each case, the translation need arises within a Workday workflow. The solution should execute within that workflow, not require leaving Workday.

## The Solution: AWS AI Services Inside Workday Orchestrations

The architecture follows the same pattern established in Part 1, with the Lambda function now calling AWS AI/ML services:

```
Workday Orchestration → External Endpoint → AWS Lambda → AWS Translate/Comprehend → Response
```

Two AWS services power this integration:

- **Amazon Translate** — Neural machine translation that supports 75+ languages with natural-sounding output. It processes text in real time (200–500ms for typical paragraph-length content) and charges per character translated ($15 per million characters).

- **Amazon Comprehend** — Natural language processing service that performs language detection, sentiment analysis, and entity extraction. When used with Translate, it eliminates the need for the user to specify their source language. Comprehend identifies the language, then Translate converts to the target.

The Lambda function acts as the bridge: it receives text and target language from Workday, optionally auto-detects the source language, calls AWS Translate, and returns the translated text in a format Workday can consume.

## Technical Walkthrough

### Prerequisites

Same as Part 1, plus:
- AWS account with access to Amazon Translate and Amazon Comprehend (enabled by default in most regions)
- Workday development tenant with the Extend app from Part 1 (or a new one)

### Step 1: Review the Lambda Function

Clone the repository (if you have not already) and navigate to the translate sample:

```bash
cd sample-workday-aws-integrations/workday-extend-examples/workday-translate-sample/sam-version
```

The Lambda handler (`src/index.py`):

```python
import json
import boto3

translate = boto3.client('translate')

def handler(event, context):
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event
        
        text = body.get('text', '')
        source_lang = body.get('sourceLanguage', 'auto')
        target_lang = body.get('targetLanguage', 'en')
        
        if not text:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Text is required'})
            }
        
        result = translate.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'translatedText': result['TranslatedText'],
                'sourceLanguage': result['SourceLanguageCode'],
                'targetLanguage': result['TargetLanguageCode']
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

Key design decisions in this function:

1. **Auto-detection by default.** The `sourceLanguage` parameter defaults to `'auto'`. When set to `'auto'`, AWS Translate calls Amazon Comprehend internally to detect the source language before translating. This means the Workday orchestration does not need to know what language the input is in.

2. **Flexible input handling.** The function accepts both direct JSON events (when invoked directly via `aws lambda invoke`) and API Gateway-style events (where the payload is in a `body` string). This makes it testable locally and compatible with different invocation patterns.

3. **Structured error responses.** The function returns consistent JSON with `statusCode` and `body` fields regardless of success or failure. The Workday orchestration can check `statusCode` to determine whether to use the result or route to an error handler.

4. **Boto3 client initialization outside the handler.** The `translate` client is created at module level, outside the handler function. This means it is reused across warm invocations (Lambda container reuse), avoiding the overhead of creating a new client on every call.

### Step 2: Review the SAM Template

The `template.yaml` for this example adds IAM permissions for the AI services:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Workday Extend AWS Translate Sample

Resources:
  TranslateFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: WorkdayTranslateFunction
      Runtime: python3.11
      Handler: index.handler
      CodeUri: src/
      Role: '{{resolve:ssm:/workday-extend-tenant-config/LambdaExecutionRole}}'
      VpcConfig:
        SecurityGroupIds:
          - '{{resolve:ssm:/workday-extend-tenant-config/LambdaSecurityGroup}}'
        SubnetIds:
          - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet1}}'
          - '{{resolve:ssm:/workday-extend-tenant-config/VPCSubnet2}}'
      Policies:
        - Statement:
          - Effect: Allow
            Action:
              - translate:TranslateText
              - comprehend:DetectDominantLanguage
            Resource: '*'

Outputs:
  FunctionName:
    Description: Lambda function name for Workday Extend
    Value: !Ref TranslateFunction
  FunctionArn:
    Description: Lambda function ARN for Workday Extend
    Value: !GetAtt TranslateFunction.Arn
```

Compared to the Sum example from Part 1, this template adds:

- **`Policies` block** — Grants the Lambda function permission to call `translate:TranslateText` and `comprehend:DetectDominantLanguage`. These are the minimum IAM actions required. The `Resource: '*'` is appropriate here because Translate and Comprehend do not operate on specific resource ARNs (they are stateless API calls).

- **`FunctionName`** — Explicitly names the function `WorkdayTranslateFunction` for easy identification in the Workday Extend endpoint configuration.

- **`Outputs`** — Exports both the function name and ARN for reference when configuring the Workday external endpoint.

The VPC configuration and execution role remain identical to Part 1. The Lambda function still deploys into the Workday-managed VPC with network isolation. AWS Translate and Comprehend are accessed through VPC endpoints provisioned in the Workday tenant's VPC.

### Step 3: Deploy

```bash
sam build && sam deploy
```

### Step 4: Test Locally and in AWS

**Local testing:**

```bash
sam local invoke TranslateFunction --event events/test-event.json
```

Sample test event (`events/test-event.json`):

```json
{
  "text": "Hello world, this is a test translation",
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

Expected response:

```json
{
  "statusCode": 200,
  "body": "{\"translatedText\": \"Hola mundo, esta es una traducción de prueba\", \"sourceLanguage\": \"en\", \"targetLanguage\": \"es\"}"
}
```

**Testing auto-detection** (omit `sourceLanguage`):

```json
{
  "text": "Bonjour le monde, ceci est un test",
  "targetLanguage": "en"
}
```

The function detects French automatically and translates to English.

**AWS testing:**

```bash
aws lambda invoke \
  --function-name WorkdayTranslateFunction \
  --payload file://test/payload.json \
  --region us-west-2 \
  output.json

cat output.json
```

### Step 5: Configure the Workday Orchestration

The Workday side configuration follows the same pattern as Part 1, with adjustments for the translation-specific parameters:

1. **Create the External Endpoint** — Point to `WorkdayTranslateFunction`. Define the request schema with three fields: `text` (required string), `sourceLanguage` (optional string, defaults to auto), `targetLanguage` (required string).

2. **Build a Translation Orchestration** — Create an orchestration that:
   - Accepts input: text to translate, target language code
   - Optionally accepts source language (or lets auto-detection handle it)
   - Calls the external endpoint
   - Parses the response to extract `translatedText`, `sourceLanguage`, and `targetLanguage`
   - Stores the result in a Workday custom object or returns it to the calling process

3. **Wire to a Business Process (optional)** — Attach the orchestration to Workday business events. For example, trigger translation when a job description is submitted in a non-English locale, or when a support request is created.

The [WORKDAY_DEPLOYMENT_GUIDE.md](https://github.com/aws-samples/sample-workday-aws-integrations/blob/main/workday-extend-examples/workday-translate-sample/WORKDAY_DEPLOYMENT_GUIDE.md) provides step-by-step configuration with screenshots specific to the translation use case.

## Supported Languages

AWS Translate supports 75+ languages. Common language codes used in enterprise HR:

| Code | Language | Code | Language |
|------|----------|------|----------|
| `en` | English | `ja` | Japanese |
| `es` | Spanish | `ko` | Korean |
| `fr` | French | `zh` | Chinese (Simplified) |
| `de` | German | `pt` | Portuguese |
| `it` | Italian | `ar` | Arabic |
| `hi` | Hindi | `nl` | Dutch |

When `sourceLanguage` is set to `'auto'`, the service detects the input language from the text itself. This is the recommended approach for user-generated content where the input language is unpredictable.

## Architecture Considerations

### Performance

- **Cold start**: 1–2 seconds (first invocation after idle period)
- **Warm execution**: 200–500ms for typical paragraph-length text
- **Throughput**: AWS Translate handles bursts without pre-provisioning; Lambda concurrency scales automatically
- **Text limits**: AWS Translate accepts up to 10,000 bytes (approximately 5,000 characters) per request. For longer documents, implement chunking in the Lambda function.

### Cost

This integration is economical at enterprise scale:

- **AWS Translate**: $15.00 per million characters (first 500M characters/month in first 12 months are free tier)
- **AWS Comprehend** (language detection): $0.0001 per request (included when using `auto` source language)
- **Lambda**: $0.20 per 1M requests + compute time

**Example**: Translating 10,000 paragraphs per month (average 500 characters each) = 5 million characters = $0.075/month for translation + negligible Lambda cost.

### Security

- Text is processed in memory and not stored by AWS Translate (unless you opt into custom terminology or parallel data features)
- The Lambda function runs in the Workday-managed VPC with no public internet route
- IAM permissions are scoped to only `translate:TranslateText` and `comprehend:DetectDominantLanguage`
- No translation data is logged to CloudWatch by default (add logging explicitly if needed for debugging)

### Extending This Example

The base translate function can be enhanced for production use:

| Enhancement | Implementation |
|---|---|
| **Batch translation** | Accept an array of text objects, loop through `translate_text` calls, return all results |
| **Custom terminology** | Upload domain-specific glossaries (benefits terms, job titles) via AWS Translate custom terminology |
| **Translation memory** | Store translations in DynamoDB; check cache before calling Translate to reduce cost and improve consistency |
| **Format preservation** | Set `Settings={'Formality': 'FORMAL'}` for professional HR communications |
| **Profanity masking** | Set `Settings={'Profanity': 'MASK'}` for user-generated content |
| **Quality metrics** | Track translation volume, language pairs, and latency in CloudWatch custom metrics |

## Real-World Use Cases in Workday

This translation service enables several high-value workflows:

**Global communications.** An HR leader publishes a company-wide announcement in English. A Workday business process triggers the translation orchestration for each employee's preferred language (stored in their Workday profile). Translated versions are delivered through Workday notifications.

**Multi-language job postings.** A recruiter writes a job description once. The orchestration translates it to the languages needed for each posting region. Results are stored as localized versions in Workday Recruiting.

**Employee self-service.** A custom Workday Extend app provides a "Translate" button on support request forms. Employees write in their native language; the support team sees both original and translated text.

**Compliance documentation.** Legal policies are authored in one language. The orchestration produces initial translations for all required locales. Human reviewers then refine the machine translation, cutting translation time by 60–80%.

## Conclusion and Next Steps

This post demonstrated how to add AI-powered translation to Workday workflows using AWS Translate and Comprehend. The pattern is the same foundation from Part 1 (Lambda + External Endpoint + Orchestration) with the addition of AWS AI service calls and the IAM permissions to enable them.

**To get started:**

1. Deploy the translate sample from the [sample repository](https://github.com/aws-samples/sample-workday-aws-integrations/tree/main/workday-extend-examples/workday-translate-sample).
2. Follow the [WORKDAY_DEPLOYMENT_GUIDE.md](https://github.com/aws-samples/sample-workday-aws-integrations/blob/main/workday-extend-examples/workday-translate-sample/WORKDAY_DEPLOYMENT_GUIDE.md) to configure the Workday orchestration.
3. Test with your own text and language pairs to validate quality for your domain.
4. Consider adding custom terminology for industry-specific or company-specific terms.

For an advanced example that demonstrates agentic AI with Amazon Bedrock AgentCore, Model Context Protocol (MCP), and streaming responses, see Part 3 of this series: [Building an AI Employee Onboarding Agent with Amazon Bedrock AgentCore](blog-03-ai-onboarding-agent.md).


---

## Series Navigation

- [Part 1: Getting Started with Workday Extend and AWS Lambda](blog-01-getting-started-with-lambda.md)
- **Part 2: Real-Time Translation in Workday with AWS Translate and Comprehend** (this post)
- [Part 3: Building an AI Employee Onboarding Agent with Amazon Bedrock AgentCore](blog-03-ai-onboarding-agent.md)

---

The complete source code, SAM templates, and deployment guides are available in the [aws-samples/sample-workday-aws-integrations](https://github.com/aws-samples/sample-workday-aws-integrations/tree/main/workday-extend-examples) repository on GitHub.
