import boto3
import time

def configure_lex(text): 
	"""
		Given the input text typed in by the user, calls Lex. Lex then handles the input
		with the appropriate intent, returning the response text to be displayed by the bot. 
	"""
	client = boto3.client("lex-runtime")
	lf0user = "lf0user"
	out = {
		"messages": [
			{
				"type": "unstructured", 
				"unstructured": {
					"id": lf0user, 
					"text": client.post_text(botName="DiningConcierge", 
											 botAlias="test", 
											 userId=lf0user, 
											 inputText=text)["message"],
					"timestamp": str(time.time())
				}
			}
		]
	}
	return out

def lambda_handler(event, context): 
	"""
		Driver function.
	"""
	text = event["messages"][0]["unstructured"]["text"]
	return configure_lex(text)