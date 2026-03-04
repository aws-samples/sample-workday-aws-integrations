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
