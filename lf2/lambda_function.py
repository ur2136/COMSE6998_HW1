"""
Code for LF2. Acts as queue worker:
    1. lambda_handler (the main driver) pulls a message from the SQS queue
    2. elastic_search retrieves the data for 3 random restaurants in Manhattan 
       corresponding to the cuisine mentioned in the above message
    3. send_email uses Amazon SES to send the user an email containing the recommendations
While we can invoke LF2 manually from the AWS console in order to handle messages in the 
SQS queue (Q1), we choose instead to set up a CloudWatch event trigger which monitors Q1 
to see if any new tasks have been added (by a user's interaction with the chatbot). LF2 is
called only when the event trigger detects a new task in Q1. 
"""
import json
import boto3
import random
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

USER = "kt"
PW = "shreK@!$799"
ELASTIC_SEARCH_DOMAIN = "search-newdomain-ad5lvqbm3an6taybu34h6ptmv4.us-east-1.es.amazonaws.com"

def elastic_search(message): 
    """
        Given the parameter message which indicates the user's preferred cuisine, 
        returns the data for 3 random restaurants in Manhattan categorizied under 
        the cuisine in question. The "random" effect is achieved through random.sample().
        We first use OpenSearch to quickly find the IDs of restaurants which correspond 
        to a certain cuisine, then use the IDs as primary keys in a DynamoDB query to 
        retrieve additional information about the restaurants. 
    """
    message_body = message["Body"]
    json_response = json.loads(message_body)
    region='us-east-1'
    service='es'
    credentials=boto3.Session().get_credentials()
    awsauth=AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    client = OpenSearch(
        hosts = [{"host": ELASTIC_SEARCH_DOMAIN, "port": 443}], 
        http_auth = (USER, PW), 
        # http_auth = awsauth,
        use_ssl = True, 
        verify_certs = True, 
        connection_class = RequestsHttpConnection
    )

    query_term = json_response["cuisine"]
    query = {
        "size": 100, 
        "query": {
            "multi_match": {
                "query": query_term
            }
        }
    }
    
    response = client.search(body=query)
    one, two, three = random.sample(range(0, 100), 3)
    aux = response["hits"]["hits"]
    aux = [aux[one], aux[two], aux[three]]
    restaurant_ids = [e["_id"] for e in aux]

    dynamo_client = boto3.client('dynamodb')
    dynamo_response = []
    for restaurant in restaurant_ids: 
        aux = dynamo_client.query(TableName="yelp-restaurants",
                                  KeyConditionExpression="id = :name",
                                  ExpressionAttributeValues={":name": {"S": restaurant}})  
        dynamo_response.append(aux)  
    
    return dynamo_response

def response_from_queue(): 
    """
        Retrieve the most recent element in the SQS queue and return it. 
        Element is removed from SQS afterwards (to prevent sending the same 
        email over and over again).
    """
    attribute_names = ["location", "noOfPeople", "cuisine", "dateofReservation", 
                       "timeofReservation", "emailaddress"]
    sqs_client = boto3.client('sqs')
    queue_url = "https://sqs.us-east-1.amazonaws.com/263921239677/Q1"
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=0
    )
    message = response["Messages"][0]
    sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=message["ReceiptHandle"]
    )
    return message

def lambda_handler(event, context): 
    """
        Main driver function. Error handling in the case of an empty SQS queue included.
        Error handling is necessary only when we manually invoke LF2 -- CloudWatch will 
        try to invoke LF2 only if there is an element in the queue. 
    """
    try: 
        response = response_from_queue()
        records = elastic_search(response)
        formatted_records = return_records(records)
        send_email(response, formatted_records)
        return {
            "statusCode": 200,
            "body": json.dumps("Hello from LF2!")
        }
    except KeyError: 
        print("Oops! There are no tasks to be handled in the queue.")
    
def send_email(queue_response, records):
    """
        Sends the uesr an email using SES (Simple Email Service). 
        We tried using the Simple Notification Service's email option, 
        but we found the subscribe/un-subscribe steps to be cumbersome, 
        and preferred a one-off message sender such as the SES.  
    """ 
    ses = boto3.client('ses')
    msg = compose_message(queue_response, records)
    json_response = json.loads(queue_response["Body"])
    user_email = json_response["emailaddress"]
    response = ses.verify_email_identity(EmailAddress=user_email)
    response = ses.send_email(Source="jk4534@columbia.edu", 
                              Destination={"ToAddresses": [user_email]},
                              Message={
                                  "Subject": {
                                      "Data": "Restaurant Notification", 
                                      "Charset": "UTF-8"
                                  }, 
                                  "Body": {
                                      "Text": {
                                          "Data": msg, 
                                          "Charset": "UTF-8"
                                      }
                                  }
                              })

def return_records(json_db): 
    """
        Formats records returned from OpenSearch to be appropriate for sending the user an email.
    """
    records = []
    for element in json_db: 
        current = element["Items"][0]
        name = current["name"]["S"]
        address = current["address"]["SS"]
        dict_el = {"name": name, "address": address}
        records.append(dict_el)
    return records

def compose_message(queue_response, records): 
    json_response = json.loads(queue_response["Body"])
    cuisine = json_response["cuisine"]
    noOfPeople = json_response["noOfPeople"]
    dateofReservation = json_response["dateofReservation"]
    timeofReservation = json_response["timeofReservation"]

    content = "Hello! Here are my " + cuisine + " restaurant suggestions for " + \
              noOfPeople + " people, for " + dateofReservation + " at " + \
              timeofReservation + ": \n"
    for i, record in enumerate(records): 
        content += str(i+1) + ". " + record["name"] + ", located at " + record["address"][0]
        content += "\n"
    content += "Enjoy your meal."
    return content
