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
