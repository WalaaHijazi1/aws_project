import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
import boto3
import json
from telegram import Bot
import asyncio
import uuid
from botocore.exceptions import ClientError




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
bucket_name = secrets['BUCKET_NAME']
queue_url = secrets['SQS_QUEUE_URL']
telegram_token = secrets['TELEGRAM_TOKEN']
telegram_app_url = secrets['TELEGRAM_APP_URL']
region_name = secrets.get('AWS_REGION', 'us-west-1')
dynamodb_table = secrets['DYNAMODB_TABLE']

# Initialize AWS clients

sqs = boto3.resource('sqs', region_name=region_name)
sqs_client = boto3.client('sqs', region_name=region_name)
s3_client = boto3.client('s3', region_name=region_name)
dynamodb = boto3.resource('dynamodb', region_name=region_name)


#s3 = boto3.client('s3')
#sqs = boto3.client('sqs')

def upload_image_to_s3(image_path, bucket_name):
    image_key = str(uuid.uuid4()) + '.jpg'
    try:
        s3_client.upload_file(image_path, bucket_name, image_key)
        logger.info(f'Uploaded {image_path} to S3 bucket {bucket_name} with key {image_key}')
        return image_key
    except Exception as e:
        logger.error(f'Failed to upload {image_path} to S3: {str(e)}')
        return None

def send_job_to_sqs(queue_url, image_key, chat_id):
    message = {
        'image_key': image_key,
        'chat_id': chat_id
    }
    try:
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
        logger.info(f'Sent job to SQS queue {queue_url} for image {image_key}')
    except Exception as e:
        logger.error(f'Failed to send job to SQS: {str(e)}')

async def set_webhook():
    bot = Bot(token=telegram_token)
    url = f"{telegram_app_url}/{telegram_token}"
    await bot.set_webhook(url=url)
    print(f"Webhook set to {url}")

# Run the asynchronous function
asyncio.run(set_webhook())

class Bot:
    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')




class ObjectDetectionBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if self.is_current_msg_photo(msg):
            photo_path = self.download_user_photo(msg)

            # Upload the photo to S3
            s3_key = upload_image_to_s3(photo_path, bucket_name)
            if not s3_key:
                self.send_text(msg['chat']['id'], 'Failed to upload your image. Please try again later.')
                return

            # Log the SQS message before sending
            logger.info(f'Preparing to send SQS message: image_key={s3_key}, chat_id={msg["chat"]["id"]}')

            # Send a job to the SQS queue
            send_job_to_sqs(queue_url, s3_key, msg['chat']['id'])

            # Send message to the Telegram end-user
            self.send_text(msg['chat']['id'], 'Your image is being processed. Please wait...')


if __name__ == '__main__':
    token = telegram_token
    telegram_chat_url = 'https://polybot-project.atech-bot.click'
    # telegram_chat_url = 'https://Walaa-LB-341442714.us-west-1.elb.amazonaws.com'  # Replace with your actual ALB domain
    bot = ObjectDetectionBot(token, telegram_chat_url)



















































































































'''
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile


class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class ObjectDetectionBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if self.is_current_msg_photo(msg):
            photo_path = self.download_user_photo(msg)

            # TODO upload the photo to S3
            # TODO send a job to the SQS queue
            # TODO send message to the Telegram end-user (e.g. Your image is being processed. Please wait...)
'''