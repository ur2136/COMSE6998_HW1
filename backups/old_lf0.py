# old version of lf0 (after verifying with Umang)
import json
import boto3
import time

def configure_lex(text): 
    client = boto3.client('lex-runtime')
    lf0user = "lf0user"
    out = {
            "messages": [
                            {
                              "type": "unstructured",
                              "unstructured": {
                                "id": lf0user,
                                "text": client.post_text(botName="DiningConcierge", botAlias="test", \
                                    userId=lf0user, inputText=text)['message'],
                                "timestamp": str(time.time())
                              }
                            }
                        ]
            }
    return out

# inputText will come from event or context 

def lambda_handler(event, context):
    print(event)
    text = event['messages'][0]["unstructured"]["text"]
    return configure_lex(text)
    # configure_lex should return some JSON which we return instead of the below 
    # return {
    #     'statusCode': 200,
    #     'body': json.dumps('Hello from Lambda!')
    # }


# {
#   "messages": [
#     {
#       "type": "string",
#       "unstructured": {
#         "id": "string",
#         "text": "string",
#         "timestamp": "string"
#       }
#     }
#   ]
# }