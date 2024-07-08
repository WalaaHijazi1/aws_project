import time
from pathlib import Path
import yaml
from loguru import logger
import os
import boto3
import sys
import requests
import json
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from decimal import Decimal


# Add yolov5 directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../yolov5'))
from detect import run



## Adding varibales through Secret Manager:
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
    

    secret = json.loads(secret)

    return json.loads(get_secret_value_response['SecretString'])

# Fetch the secrets
secrets = get_secret()

# Using the secrets
images_bucket = secrets['BUCKET_NAME']
queue_name = secrets['SQS_QUEUE_NAME']
region_name = secrets.get('AWS_REGION', 'us-west-1')
dynamodb_table = secrets['DYNAMODB_TABLE']
polybot_url = 'https://polybot-project.atech-bot.click/results'


print("Secrets retrieved successfully")

# Initialize AWS clients
sqs_client = boto3.client('sqs', region_name=region_name)
s3_client = boto3.client('s3', region_name=region_name)
dynamodb = boto3.resource('dynamodb', region_name=region_name)
sqs_client = boto3.client('sqs', region_name='us-west-1')
sqs_resource = boto3.resource('sqs', region_name='us-west-1')

print("AWS clients initialized successfully")



with open("coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

def download_image_from_s3(bucket, key, download_path):
    s3_client.download_file(bucket, key, download_path)

def upload_image_to_s3(bucket, key, upload_path):
    if not os.path.exists(upload_path):
        logger.error(f"File not found: {upload_path}")
        return
    try:
        s3_client.upload_file(upload_path, bucket, key)
        logger.info(f"Successfully uploaded {upload_path} to {bucket}/{key}")
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"Credentials error: {e}")
    except Exception as e:
        logger.error(f"Failed to upload {upload_path} to {bucket}/{key}: {e}")

def store_prediction_summary_in_dynamodb(table, prediction_summary):
    try:
        # Convert Decimal objects to float
        for label in prediction_summary['labels']:
            label['cx'] = float(label['cx'])
            label['cy'] = float(label['cy'])
            label['width'] = float(label['width'])
            label['height'] = float(label['height'])
        
        table.put_item(
            Item={
                'predictionId': prediction_summary['predictionid'],
                'chat_id': prediction_summary['chat_id'],  # Ensure chat_id is included
                'results': json.dumps(prediction_summary['labels']),
                'time': str(prediction_summary['time']),
                'original_img_path': prediction_summary['original_img_path'],
                'predicted_img_path': prediction_summary['predicted_img_path']
            }
        )
        logger.info(f"Successfully stored prediction {prediction_summary['predictionid']} in DynamoDB")
    except Exception as e:
        logger.error(f"Failed to store prediction in DynamoDB: {e}")

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

def consume():
    global sqs_client
    while True:
        try:
            response = sqs_client.receive_message(QueueUrl=queue_name, MaxNumberOfMessages=1, WaitTimeSeconds=5)

            if 'Messages' in response:
                message_body = response['Messages'][0]['Body']
                receipt_handle = response['Messages'][0]['ReceiptHandle']
                message = json.loads(message_body)

                # Use the MessageId as a prediction UUID
                prediction_id = response['Messages'][0]['MessageId']
                img_name = message['image_key']
                chat_id = message['chat_id']
                original_img_path = f'/tmp/{img_name}'

                logger.info(f'prediction: {prediction_id}. start processing')

                #### AUTOSCALING AND CLOUDWATCH
                AUTOSCALING_GROUP_NAME = 'AutoScaling_AWS_project'
                QUEUE_NAME = 'WalaaQueue'
                
                queue = sqs_resource.get_queue_by_name(QueueName=QUEUE_NAME)
                msgs_in_queue = int(queue.attributes.get('ApproximateNumberOfMessages'))
                asg_client = boto3.client('autoscaling', region_name='us-west-1')
                asg_groups = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[AUTOSCALING_GROUP_NAME])['AutoScalingGroups']

                if not asg_groups:
                    raise RuntimeError('Autoscaling group not found')
                else:
                    asg_size = asg_groups[0]['DesiredCapacity']

                if asg_size > 0:
                    backlog_per_instance = msgs_in_queue / asg_size

                    # Put custom metrics to CloudWatch
                    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
                    cloudwatch.put_metric_data(
                        MetricData=[
                            {
                                'MetricName': 'NumberOfMessagesReceived',
                                'Dimensions': [
                                    {
                                        'Name': 'queue',
                                        'Value': 'backlog_per_instance'
                                    },
                                ],
                                'Unit': 'Count',
                                'Value': backlog_per_instance
                            },
                        ],
                        Namespace='Walaa-aws'
                    )
                else:
                    logger.error("DesiredCapacity is zero. Cannot calculate backlog_per_instance.")

                # Download image from S3
                download_image_from_s3(images_bucket, img_name, original_img_path)
                logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')

                # Predicts the objects in the image
                run(
                    weights='yolov5s.pt',
                    data='../coco128.yaml',
                    source=original_img_path,
                    project='static/data',
                    name=prediction_id,
                    save_txt=True
                )
                logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

                # Path for the predicted image with labels
                predicted_img_path = Path(f'static/data/{prediction_id}/{img_name}')

                # Upload predicted image to S3
                predicted_s3_key = f'predictions/{prediction_id}/{predicted_img_path.name}'
                upload_image_to_s3(images_bucket, predicted_s3_key, str(predicted_img_path))

                # Parse prediction labels and create a summary
                pred_summary_path = Path(f'static/data/{prediction_id}/labels/{img_name.split(".")[0]}.txt')
                if pred_summary_path.exists():
                    with open(pred_summary_path) as f:
                        labels = f.read().splitlines()
                        labels = [line.split(' ') for line in labels]
                        labels = [{
                            'class': names[int(l[0])],
                            'cx': Decimal(l[1]),
                            'cy': Decimal(l[2]),
                            'width': Decimal(l[3]),
                            'height': Decimal(l[4]),
                        } for l in labels]

                    logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

                    # Count instances of each class
                    class_counts = {}
                    for label in labels:
                        cls = label['class']
                        if cls in class_counts:
                            class_counts[cls] += 1
                        else:
                            class_counts[cls] = 1

                    # Format the message
                    formatted_results = ', '.join([f"{cls}: {count}" for cls, count in class_counts.items()])

                    prediction_summary = {
                        'predictionid': prediction_id,
                        'chat_id': chat_id,  # Include chat_id in the summary
                        'original_img_path': original_img_path,
                        'predicted_img_path': str(predicted_img_path),
                        'labels': labels,
                        'time': Decimal(str(time.time())),
                        'receipt_handle': receipt_handle  # Include receipt_handle
                    }

                    # Store prediction summary in DynamoDB
                    table = dynamodb.Table(dynamodb_table)
                    store_prediction_summary_in_dynamodb(table, prediction_summary)

                    # Perform a GET request to Polybot to /results endpoint
                    logger.info(f"Sending GET request to Polybot: {polybot_url}?predictionId={prediction_id}&results={formatted_results}&receiptHandle={receipt_handle}")
                    requests.get(f"{polybot_url}?predictionId={prediction_id}&results={formatted_results}&receiptHandle={receipt_handle}")

                # Delete the message from the queue as the job is considered as DONE
                logger.info(f"Deleting message from SQS: {receipt_handle}")
                sqs_client.delete_message(QueueUrl=queue_name, ReceiptHandle=receipt_handle)
                logger.info(f"Deleted message with prediction ID {prediction_id} from the queue")

        except Exception as e:
            logger.error(f"Error in consume function: {e}")

if __name__ == "__main__":
    consume()
