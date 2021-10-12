import json
import boto3
import datetime
import time
import os
import re
import dateutil.parser
import logging

regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# --- Helpers that build all of the responses ---

def elicit_intent(session_attributes, message):
    """
    Invokes Elicit Intent Dialog Action.
    """
  return {
         'sessionAttributes': session_attributes,
         'dialogAction': {
            'type': 'ElicitIntent',
            'message': message
         }
     }

def close(session_attributes, fulfillment_state, message):
    """
    Invokes Close Dialog Action.
    """
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    """
    Invokes Elicit Slot Dialog Action.
    """
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    """
    Invokes Delegate Dialog Action.
    """
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

# --- Getter Functions ---

def get_slots(request):
    """
    Gets all the slots from request.
    """
    return request['currentIntent']['slots']

def get_slot(request, slotName):
    """
    Gets the requested slot from request.
    """
    slots = get_slots(request)
    if slots is not None and slots[slotName] is not None:
        return slots[slotName]
    else:
        return None
       
def get_session_attributes(request):
    """
    Gets the session attributes from request.
    """
   if 'sessionAttributes' in request:
        return request['sessionAttributes']
   else:
        return {}

# --- Helper Functions ---

def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n

""" --- Validation Functions --- """

def isvalid_location(location):
    """
    Checks if location is manhattan.
    """
    valid_locations = ['manhattan']
    return location.lower() in valid_locations

def isvalid_cuisine(cuisine):
    """
    CHecks if cuisine is one of the acceptable cuisine_types.
    """
    cuisine_types = ['indian', 'mexican', 'italian', 'chinese', 'spanish', 'japanese']
    return cuisine.lower() in cuisine_types

def isvalid_nopeople(noOfPeople):
    """
    Checks if number of people is a positive integer.
    """
    if safe_int(noOfPeople)>0:
        return True
    return False

def isvalid_date(dateofReservation):
    """
    Checks if date of reservation is not before current date.
    """
    try:
        user_time = dateutil.parser.parse(dateofReservation)
        now_time = datetime.datetime.now()-datetime.timedelta(hours=4)
        now_time = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return user_time >= now_time
    except ValueError:
        return False

def isvalid_time(timeofReservation,dateofReservation):
    """
    Checks if the time of reservation is valid i.e. user can only make reservations AFTER current time.
    """
    a = datetime.datetime.now()-datetime.timedelta(hours=4)
    a = a.replace(hour=0, minute=0, second=0, microsecond=0)
    a = datetime.datetime(a.year,a.month,a.day)
    if datetime.datetime.strptime(dateofReservation, '%Y-%m-%d').date() == a.date():
        now = datetime.datetime.now()-datetime.timedelta(hours=4)
        hour = datetime.datetime.strptime(timeofReservation, '%H:%M').time().hour
        minute_ = datetime.datetime.strptime(timeofReservation, '%H:%M').time().minute
        time = now.replace(hour=hour, minute=minute_, second=0, microsecond=0)
        return time >= now
    else:
        return True

def isvalid_email(emailaddress):
    """
    Checks if the email address is valid.
    """
    if (re.search(regex, emailaddress)):
        return True
    else:
        return False

def build_validation_result(isvalid, violated_slot, message_content):
    """
    Builds the response if a validation check fails.
    """
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_book_reservation(intent_request):
    """
    Performs validation on all the slots passed during the DiningSuggestionsIntent
    """
    location = get_slot(intent_request, 'location')
    cuisine = get_slot(intent_request,'cuisine')
    noOfPeople = get_slot(intent_request,'noOfPeople')
    dateofReservation = get_slot(intent_request,'dateofReservation')
    timeofReservation = get_slot(intent_request,'timeofReservation')
    emailaddress = get_slot(intent_request,'emailaddress')
    if location and not isvalid_location(location):
        return build_validation_result(
            False,
            'location',
            'We currently do not support {} as a valid destination.  Can you try a different city?'.format(location)
        )
       
    if cuisine and not isvalid_cuisine(cuisine):
        return build_validation_result(
            False,
            'cuisine',
            'I did not recognize that cuisine.  What cuisine would you like to try?')
           
    if noOfPeople and not isvalid_nopeople(noOfPeople):
        return build_validation_result(
            False,
            'noOfPeople',
            'Please enter a positive number.'
        )

    if dateofReservation and not isvalid_date(dateofReservation):
        return build_validation_result(
            False,
            'dateofReservation',
            'I did not understand your reservation date.  What date would you like to make your reservation on?'
        )

    if timeofReservation and not isvalid_time(timeofReservation, dateofReservation):
        return build_validation_result(
            False,
            'timeofReservation',
            'I did not understand your reservation time.  When would you like to make your reservation?'
        )
   
    if emailaddress and not isvalid_email(emailaddress):
        return build_validation_result(False, 'emailaddress', 'Please enter a valid id')
 
    return {'isValid': True}
   
""" --- SQS --- """

def sqsRequest(request):
    """
    Adds inputs supplied by the user to the SQS queue using boto3.
    """
    sqs_client = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/263921239677/Q1'
    messageContent = {
        'location': request['location'],
        'noOfPeople': request['noOfPeople'],
        'cuisine': request['cuisine'],
        'dateofReservation': request['dateofReservation'],
        'timeofReservation': request['timeofReservation'],
        'emailaddress': request['emailaddress']
    }

   response = sqs_client.send_message(
        QueueUrl = queue_url,
        # MessageAttributes = messageContent,
        MessageBody = json.dumps(messageContent)
        )
   
    print ('send data to queue')
    print("Response : ", response)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

""" --- Intent Handlers --- """

def greeting_intent_handler(request):
  """
  Handler for Greeting Intent.
  """
  session_attributes = get_session_attributes(request)
  text = 'Hi there, how can I help?'
  message = {
      'contentType': 'PlainText',
      'content': text
  }
  dialog_action_type= 'ElicitIntent'
  return elicit_intent(session_attributes,message)

def thank_you_intent_handler(request):
  """
  Handler for Thank You Intent.
  """
  session_attributes = get_session_attributes(request)
  text = 'You’re welcome.'
  message = {
      'contentType': 'PlainText',
      'content': text
  }
   
  fulfillment_state= "Fulfilled"
  return close(session_attributes,fulfillment_state,message)

def dining_suggestions_intent_handler(intent_request):
    """
    Handler for Dining Suggestions Intent.
    """
    location = get_slot(intent_request,'location')
    cuisine = get_slot(intent_request,'cuisine')
    noOfPeople = get_slot(intent_request,'noOfPeople')
    dateofReservation = get_slot(intent_request,'dateofReservation')
    timeofReservation = get_slot(intent_request,'timeofReservation')
    emailaddress = get_slot(intent_request,'emailaddress')
    session_attributes = get_session_attributes(intent_request)
   
    restaurant_req = json.dumps({
        'location': location,
        'noOfPeople': noOfPeople,
        'cuisine': cuisine,
        'dateofReservation': dateofReservation,
        'timeofReservation': timeofReservation,
        'emailaddress': emailaddress
    })
   
    if intent_request['invocationSource'] == 'DialogCodeHook':
        validation_result = validate_book_reservation(intent_request)
        if not validation_result['isValid']:
            slots = get_slots(intent_request)
            slots[validation_result['violatedSlot']] = None
            logger.debug(validation_result['violatedSlot'])
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        return delegate(session_attributes,get_slots(intent_request))
         

    text = 'You’re all set. Expect my suggestions shortly! Have a good day.'
    message = {
      'contentType': 'PlainText',
      'content': text
    }
    fulfillment_state= "Fulfilled"
    dialog_action_type= 'ElicitIntent'
    sqsRequest(json.loads(restaurant_req))
    return close(session_attributes, fulfillment_state, message)

# --- Dispatcher ---

def dispatch(intent_request):
    """
    Dispatches incoming request to corresponding handler.
    """
    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'GreetingIntent':
        return greeting_intent_handler(intent_request)
    elif intent_name == 'DiningSuggestionsIntent':
        return dining_suggestions_intent_handler(intent_request)
    elif intent_name == 'ThankYouIntent':
        return thank_you_intent_handler(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---

def lambda_handler(event, context):
  """
  Driver Function.
  """
  return dispatch(event)