import flask
from flask import request
import os
from bot import ObjectDetectionBot

import boto3
import json

from telegram import Bot as TelegramBot
import asyncio

import telebot
from loguru import logger
from telebot.types import InputFile
from botocore.exceptions import ClientError



# Initialize the bot
app = flask.Flask(__name__)


def get_secret():

    secret_name = "Walaa-SecretKey"
    region_name = "us-west-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    
    return json.loads(get_secret_value_response['SecretString'])



# Fetch the secrets
secrets = get_secret()


# Using the secrets
images_bucket = secrets['BUCKET_NAME']
queue_name = secrets['SQS_QUEUE_NAME']
region_name = secrets.get('AWS_REGION', 'us-west-1')
dynamodb_table = secrets['DYNAMODB_TABLE']
telegram_token = secrets['TELEGRAM_TOKEN']
telegram_app_url = secrets['TELEGRAM_APP_URL']

# Initialize AWS clients
sqs = boto3.client('sqs', region_name=region_name)
sqs = boto3.resource('sqs', region_name=region_name)
s3 = boto3.client('s3', region_name=region_name)
dynamodb = boto3.resource('dynamodb', region_name=region_name)


@app.route('/')
def home():
    return "Hello, this is the home page!"

@app.route(f'/{telegram_token}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'

@app.route(f'/results/', methods=['GET'])
def results():
    prediction_id = request.args.get('predictionId')
    formatted_results = request.args.get('results', '')
    receipt_handle = request.args.get('receiptHandle', '')

    # Retrieve the prediction from DynamoDB
    logger.info(f"Retrieving prediction for ID: {prediction_id}")
    item = get_prediction(prediction_id)
    
    # Log the retrieved item
    logger.info(f"Retrieved item: {item}")
    
    if item:
        chat_id = int(item.get("chat_id"))
        if not chat_id:
            logger.error(f"chat_id not found in the item for prediction ID {prediction_id}")
            return 'chat_id not found', 400
        
        bot.send_text(chat_id, formatted_results)
        
        # Delete the message from the queue as the job is considered as DONE
        if receipt_handle:
            try:
                logger.info(f"Deleting message from SQS: {receipt_handle}")
                sqs.delete_message(QueueUrl=queue_name, ReceiptHandle=receipt_handle)
                logger.info(f"Deleted message with prediction ID {prediction_id} from the queue")
            except Exception as e:
                logger.error(f"Failed to delete message from queue: {e}")
        
        return 'Ok'
    else:
        logger.error(f"Prediction not found for ID {prediction_id}")
        return 'Prediction not found', 404

@app.route(f'/listItems/', methods=['GET'])
def list_items():
    items = list_all_items()
    return json.dumps(items, indent=4, default=str)

@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'

def get_prediction(prediction_id):
    table = dynamodb.Table(dynamodb_table)
    try:
        response = table.get_item(Key={'predictionId': prediction_id})
        if 'Item' in response:
            return response['Item']
        else:
            return None
    except Exception as e:
        logger.error(f"Error retrieving prediction from DynamoDB: {e}")
        return None

def list_all_items():
    table = dynamodb.Table(dynamodb_table)
    try:
        response = table.scan()
        items = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        logger.info(f"Retrieved {len(items)} items from DynamoDB")
        return items
    except Exception as e:
        logger.error(f"Error scanning DynamoDB: {e}")
        return []
        
        
        
if __name__ == "__main__":
    telegram_chat_url = telegram_app_url
    bot = ObjectDetectionBot(telegram_token, telegram_chat_url)
    app.run(host='0.0.0.0', port=8443)





























































































































'''
import flask
from flask import request
import os
from bot import ObjectDetectionBot

app = flask.Flask(__name__)


# TODO load TELEGRAM_TOKEN value from Secret Manager
TELEGRAM_TOKEN = ...

TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


@app.route(f'/results/', methods=['GET'])
def results():
    prediction_id = request.args.get('predictionId')

    # TODO use the prediction_id to retrieve results from DynamoDB and send to the end-user

    chat_id = ...
    text_results = ...

    bot.send_text(chat_id, text_results)
    return 'Ok'


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    app.run(host='0.0.0.0', port=8443)
''' 