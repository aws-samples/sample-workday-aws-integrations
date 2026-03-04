# Lambda Calc Sample

This project creates a simple AWS Lambda function using the AWS CDK (Python).
The Lambda takes two parameters `a` and `b` and returns their sum.

## Project Structure
- `lambda_function/lambda_function.py` → Lambda handler
- `lambda_stack.py` → CDK stack definition
- `app.py` → CDK app entry point
- `requirements.txt` → Dependencies

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Bootstrap CDK (if first time):
   ```bash
   cdk bootstrap
   ```

4. Deploy:
   ```bash
   cdk deploy
   ```

## Testing the Lambda

You can invoke the Lambda with:
```bash
aws lambda invoke   --function-name LambdaCalcStack-CalcLambdaXXXX   --payload '{"a": 10, "b": 20}'   response.json

cat response.json
```

Expected output:
```json
{
  "statusCode": 200,
  "body": "{\"a\": 10, \"b\": 20, \"result\": 30}"
}
```
