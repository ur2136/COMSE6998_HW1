"""
    Verified working version of LF2 (after testing with Umang). 
"""
import json
import boto3
import random
from opensearchpy import OpenSearch, RequestsHttpConnection

USER = "kt"
PW = "HereIn799@!$"
ELASTIC_SEARCH_DOMAIN = 'search-newdomain-ad5lvqbm3an6taybu34h6ptmv4.us-east-1.es.amazonaws.com'

def elastic_search(message): # before the argument was response
    message_body = message["Body"]
    # print(json.loads(message_body))
    json_response = json.loads(message_body)

    client = OpenSearch(
        hosts = [{'host': ELASTIC_SEARCH_DOMAIN, 'port': 443}],
        http_auth = (USER, PW),
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    
    q = json_response['cuisine']
    query = {
      'size': 100,
      'query': {
        'multi_match': {
          'query': q
        }
      }
    }
    
    response = client.search(body = query)
    
    one, two, three = random.sample(range(0, 100), 3) # in order to generate restaurants randomly
    aux = response["hits"]["hits"]
    aux = [aux[one], aux[two], aux[three]]
    restaurant_ids = [e["_id"] for e in aux]
    
    # restaurant_ids = [e["_id"] for e in response["hits"]["hits"]]
    dynamoclient = boto3.client('dynamodb')
    dynamoresponse = []
    for id in restaurant_ids: 
      aux = dynamoclient.query(TableName="yelp-restaurants", KeyConditionExpression="id = :name", ExpressionAttributeValues={":name": {"S": id}})
      dynamoresponse.append(aux)
    return dynamoresponse


def response_from_queue():
  attribute_names = ['location','noOfPeople','cuisine','dateofReservation','timeofReservation','emailaddress']
  sqs_client = boto3.client('sqs')
  queue_url = 'https://sqs.us-east-1.amazonaws.com/263921239677/Q1'
  response = sqs_client.receive_message(
      QueueUrl= queue_url,
      MaxNumberOfMessages=1,
      WaitTimeSeconds=0
  )
  message = response["Messages"][0]
  sqs_client.delete_message(
    QueueUrl = queue_url,
    ReceiptHandle = message["ReceiptHandle"]
    )
  return message
    
def lambda_handler(event, context):
  try: 
    response = response_from_queue()
    
    records = elastic_search(response)
    formatted_records = return_records(records)
    send_email(response,formatted_records)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
  except KeyError: 
    print("Oops! There are no tasks in the queue.")
    
def return_records(json_db):
  records = []
  print(json_db)
  for element in json_db: 
    current = element["Items"][0]
    name = current["name"]["S"]
    address = current["address"]["SS"]
    dict_el = {'name': name, 'address': address}
    records.append(dict_el)
  return records
  
def send_email(queue_response, records): 
  ses = boto3.client('ses')
  msg = compose_message(queue_response, records)
  json_response = get_values_from_queue_response(queue_response)
  user_email = json_response['emailaddress']
  response = ses.verify_email_identity(EmailAddress = user_email)
  response = ses.send_email(Source="jk4534@columbia.edu", Destination={'ToAddresses': [user_email]},
  Message={"Subject": 
    {
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
  

# def send_email(queue_response,records):
#   sns = boto3.client('sns', region_name='us-east-1')
#   topic_name = 'restaurant-recommendations'
#   msg = compose_message(queue_response,records)
#   json_response = get_values_from_queue_response(queue_response)
#   user_email = json_response['emailaddress']
#   tpcArn = 'arn:aws:sns:us-east-1:263921239677:restaurant-recommendations'
 
#   subs = sns.subscribe(
#       TopicArn=tpcArn,
#       Protocol='email',
#       Endpoint= user_email,
#       ReturnSubscriptionArn = True
#   )
#   response = sns.publish(TopicArn = tpcArn, Message=msg)
#   print(response)
#   sns.unsubscribe(response["SubscriptionArn"])

def compose_message(queue_response,records):
    json_response = get_values_from_queue_response(queue_response)
    cuisine = json_response['cuisine']
    noOfPeople = json_response['noOfPeople']
    dateofReservation = json_response['dateofReservation']
    timeofReservation = json_response['timeofReservation']
    content ='Hello! Here are my ' + cuisine + ' restaurant suggestions for ' + noOfPeople + ' people, for ' + dateofReservation + ' at '+ timeofReservation +': \n'
    for index in range(len(records)):
          print(records[index])
          content +=  (str(index+1) +'. '+ records[index]['name'] + ', located at ' + records[index]['address'][0])
          content += '\n'
    content+='Enjoy your meal.'
    return content
    
def get_values_from_queue_response(response):
    json_response = json.loads(response["Body"])
    return json_response