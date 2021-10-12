# COMSE6998_HW1
HW1 : Dining Concierge AI Agent

Name : Katie Jooyoung Kim
UNI : jk4534

Name : Umang Raj
UNI : ur2136

--------------------------------------------------------------------------------------------------------------------------------------------------------------------

S3 Bucket URL : http://jk4534ur2136.s3-website-us-east-1.amazonaws.com/

Lambdas : 
LF0 - This uses the request-response model defined in the Swagger API Specification to perform the chat operation with the lex bot.
LF1 - This is used by the lex bot as an initialization and validation code hook for 'DiningSuggestionsIntent' and a fulfillment code hook for 'GreetingIntent', 'DininingSuggestionsIntent' and 'ThankYouIntent'. This lambda also adds the data gathered from the user into an SQS queue, Q1.
LF2 - This is used to fetch data from the SQS queue Q1, gets 3 random restaurant recommendations for the cuisine collected through conversation from ElasticSearch and DynamoDB and sends them over an email, using SES.

CloudWatchTrigger : 
<name-of-trigger> - It runs every minute and invokes LF2 as a result.
