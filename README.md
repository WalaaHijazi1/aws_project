
░█████╗░░██╗░░░░░░░██╗░██████╗  ██████╗░██████╗░░█████╗░░░░░░██╗███████╗░█████╗░████████╗
██╔══██╗░██║░░██╗░░██║██╔════╝  ██╔══██╗██╔══██╗██╔══██╗░░░░░██║██╔════╝██╔══██╗╚══██╔══╝
███████║░╚██╗████╗██╔╝╚█████╗░  ██████╔╝██████╔╝██║░░██║░░░░░██║█████╗░░██║░░╚═╝░░░██║░░░
██╔══██║░░████╔═████║░░╚═══██╗  ██╔═══╝░██╔══██╗██║░░██║██╗░░██║██╔══╝░░██║░░██╗░░░██║░░░
██║░░██║░░╚██╔╝░╚██╔╝░██████╔╝  ██║░░░░░██║░░██║╚█████╔╝╚█████╔╝███████╗╚█████╔╝░░░██║░░░
╚═╝░░╚═╝░░░╚═╝░░░╚═╝░░╚═════╝░  ╚═╝░░░░░╚═╝░░╚═╝░╚════╝░░╚════╝░╚══════╝░╚════╝░░░░╚═╝░░░





█░█░█ █▀▀ █░░ █▀▀ █▀█ █▀▄▀█ █▀▀   ▀█▀ █▀█   █░█░█ ▄▀█ █░░ ▄▀█ ▄▀█ ░   █▀ ▄▀█ █▀▄▀█ █▀▀ █▀█   ▄▀█ █▄░█ █▀▄   █▄░█ █▀█ █░█ █▀█
▀▄▀▄▀ ██▄ █▄▄ █▄▄ █▄█ █░▀░█ ██▄   ░█░ █▄█   ▀▄▀▄▀ █▀█ █▄▄ █▀█ █▀█ █   ▄█ █▀█ █░▀░█ ██▄ █▀▄   █▀█ █░▀█ █▄▀   █░▀█ █▄█ █▄█ █▀▄

▄▀█ █░█░█ █▀   █▀█ █▀█ █▀█ ░░█ █▀▀ █▀▀ ▀█▀   ▀ ▀▄
█▀█ ▀▄▀▄▀ ▄█   █▀▀ █▀▄ █▄█ █▄█ ██▄ █▄▄ ░█░   ▄ ▄▀



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



THE RESULT:

