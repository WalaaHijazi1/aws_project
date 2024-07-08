
<img src="https://github.com/WalaaHijazi1/aws_project/assets/151656646/57eca09f-cea3-415b-acbc-a7c51fd737d5.jpg" width="850" height="200">


# Project Files and Directories

## polybot1
The `polybot` directory contains the source code and configuration files for the Polybot service. This service is responsible for handling interactions with the Telegram bot, uploading images to S3, sending job messages to SQS, and informing the user about the processing status.

## polybot2
The `polybot2` directory contains the source code and configuration files for the Polybot service running on the second machine. This includes the implementation of the Telegram bot and the logic for handling user interactions and processing images.

## yolo5
The `yolo5` directory contains the service files for the YOLOv5 object detection model. This service is responsible for downloading images from S3, processing them using the YOLOv5 model, and writing the results to DynamoDB. It includes the necessary scripts and configurations to run the YOLOv5 service within a Docker container.

## yolov5
This file is a cloned repository from: https://github.com/ultralytics/yolov5 .
It has all the packages that is needed to function the YoloV5 app, and explenation about the AI tool, and it's function.

## AWS - Final Project.pptx
This is the final presentation for the AWS project. It contains slides summarizing the project's goals, architecture, implementation details, and results. This presentation can be used to showcase the project to stakeholders or during a project review.

### Additional Details

- **polybot**: The main components of the Polybot service, including message handling, image upload to S3, and job submission to SQS.
- **polybot2**: The Polybot service setup for the second machine, handling similar functionalities as the main Polybot service.
- **yolo5**: Scripts and configurations for the YOLOv5 service, including code for consuming jobs from SQS, processing images, and writing results to DynamoDB.
- **yolov5**: Supporting files and additional configurations for the YOLOv5 model, ensuring the object detection service runs smoothly.
- **AWS - Final Project.pptx**: A comprehensive presentation outlining the project's objectives, design, and outcomes.


# ObjectDetectionBot Setup and Workflow

## EC2 Instance and AMI Setup
1. **Create EC2 Instance**:
   - Launched an EC2 instance of type `t2.micro`.
   
2. **Create AMI**:
   - Created an AMI image from the instance.
   - Once the AMI image status is `available`, launched a new instance from the AMI image.

## Setting Up the Load Balancer and Certificates
1. **Create Application Load Balancer (ALB)**:
   - Navigate to EC2 console under "Load Balancing" → "Create Load Balancer" → "Create" under "Application Load Balancer".
   - Configure the ALB with a name and select at least two availability zones for high availability.
   - Ensure the ALB listens on port 443 (HTTPS) and port 80 (HTTP).
   - Attach an SSL certificate from AWS ACM (Amazon Certificate Manager) for HTTPS protocol.

2. **Issue SSL Certificate**:
   - Go to ACM service in AWS and request a certificate.
   - Provide the domain name managed by Route 53.
   - Use DNS validation for the certificate request.
   - Wait for the certificate status to change from 'pending validation' to 'issued'.

3. **Configure Route 53**:
   - Go to Route 53 service and select the appropriate hosted zone.
   - Create a record with the name `polybot-project.atech-bot.click` and set the value to the DNS name of the ALB, with record type 'CNAME'.

4. **Update Load Balancer**:
   - After the certificate is issued, add a new listener to the ALB for HTTPS on port 443.
   - Forward requests to the target group containing the EC2 instances.

5. **Create Target Group**:
   - Configure the target group with target type 'instances' and protocol HTTP on port 8443.
   - Set up health checks on port 8443 with the path '/'.
   - Add the EC2 instances to the target group.

## Deploying Polybot Service
1. **Install Docker**:
   - Follow Docker installation steps from the [official Docker documentation](https://docs.docker.com/engine/install/ubuntu/).

2. **Run Polybot Service**:
   - Navigate to the polybot project directory:
     ```sh
     cd aws_project/polybot
     ```
   - Build and run the Docker container:
     ```sh
     docker build -t polybot .
     docker run -d --restart=always --name polybot-container \
       -e TELEGRAM_TOKEN=<Your_Telegram_Token> \
       -e TELEGRAM_APP_URL='https://polybot-project.atech-bot.click' \
       -e BUCKET_NAME=<Your_Bucket_Name> \
       -e SQS_QUEUE_URL=<Your_SQS_URL> \
       polybot
     ```
### NOTE: 
We used a Secret Manager for all the variables we passed for the project.
more about secret manager: https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html

## Workflow Process

### 1. Telegram Bot Configuration
- The Telegram bot sends webhook requests to: `https://polybot-project.atech-bot.click:8443/<telegram_token>`.
- The custom domain `polybot-project.atech-bot.click` is managed by Amazon Route 53.

### 2. Load Balancer Configuration
- The ALB listens on port 443 for HTTPS and port 80 for HTTP.
- The ALB distributes incoming HTTPS traffic across instances in the target group.
- The ALB routes traffic to multiple EC2 instances in different Availability Zones for high availability.
- Each EC2 instance runs the Polybot service within a Docker container on port 8443.
- The EC2 instance security group allows inbound traffic from the ALB security group on port 8443.

### 3. Web Server Setup
- A Python script sets up a web server using Flask, listening on port 8443.
- The server handles HTTP requests and starts an instance of `ObjectDetectionBot`.

### PolyBot Activation Flow (From the presentation Above):

<img src="https://github.com/WalaaHijazi1/aws_project/assets/151656646/937bd80a-172f-4504-bbed-cc147e90ecf6.jpg" width="750" height="300">


### Message Handling
#### 1. Receiving Messages
- The server receives messages sent to the Telegram bot as HTTP POST requests at the webhook URL.
- The webhook URL is mapped to a function in the script using Flask's `@app.route` decorator.
- This function processes the incoming message, passes it to `ObjectDetectionBot` for handling, and responds appropriately.

#### 2. Processing Messages
- The `ObjectDetectionBot` can handle different types of messages, such as text and photos.
- For photo messages:
  - The bot logs the incoming message and sends a confirmation or echo message back to the user.
  - The bot downloads the photo from Telegram.
  - The bot uploads the photo to an S3 bucket.
  - The bot sends a job message to an SQS queue with the image details (e.g., S3 URL) and Telegram chat_id.
  - The bot informs the user that the image is being processed.

### Image Processing Workflow: User to Yolo5 Service Integration (From the presentation Above):

<img src="https://github.com/WalaaHijazi1/aws_project/assets/151656646/e8a8dab9-9489-438a-967d-b6f43dae4008.jpg" width="750" height="300">


### Yolo5 Service Processing
#### 1. Polling SQS Queue
- The Yolo5 service, running on an EC2 instance, polls the SQS queue for new job messages.

#### 2. Processing Image
- Upon receiving a job message, Yolo5 downloads the image from S3 using the URL provided.
- Yolo5 processes the image using the YOLOv5 model to identify objects.
- Yolo5 writes the prediction results to DynamoDB.

#### 3. Informing Polybot
- Yolo5 sends a GET HTTP request to Polybot's `/results?predictionId=<predictionId>` endpoint, including the `predictionId`.

#### 4. Retrieving Results
- Polybot retrieves the results from DynamoDB based on the `predictionId`.
- Polybot sends the results back to the user on Telegram, listing all detected objects in the image.

### YOLO5 ---> PolyBot Communication (From the presentation Above):

<img src="https://github.com/WalaaHijazi1/aws_project/assets/151656646/9c4e5bf8-e948-4a14-bf02-92bc02369058.jpg" width="800" height="400">

### Autoscaling the Yolo5 Service
#### 1. MetricStreamer Microservice
- MetricStreamer runs periodically (every 30 seconds).
- It calculates the `BacklogPerInstance` metric, which is the number of messages in the SQS queue divided by the number of currently running Yolo5 instances in the Auto Scaling Group (ASG).

#### 2. Sending Metric to CloudWatch
- MetricStreamer sends the `BacklogPerInstance` metric to CloudWatch every 30 seconds.

#### 3. CloudWatch Alarm and Scaling Policy
- Configure a CloudWatch alarm to monitor the `BacklogPerInstance` metric.
- Create a target tracking scaling policy for the ASG based on the `BacklogPerInstance` metric. For example, if `BacklogPerInstance` exceeds 10, trigger a scale-out event to add more Yolo5 instances.

#### 4. Scaling Action
- When the CloudWatch alarm triggers, the ASG adjusts the number of Yolo5 instances based on the scaling policy. If `BacklogPerInstance` is high, it will scale out by adding more instances. If it's low, it will scale in by terminating instances.


### Dynamic Autoscaling of Yolo5 Service Based on SQS Queue Metrics (From the presentation Above):


<img src="https://github.com/WalaaHijazi1/aws_project/assets/151656646/f69af6cf-0c30-4b1f-ad8a-af899cbe4b3e.jpg" width="800" height="400">


## THE RESULT:

<img src="https://github.com/WalaaHijazi1/aws_project/assets/151656646/33395f12-115d-49ce-8f33-91137aab8b4d.jpg" width="500" height="450">


