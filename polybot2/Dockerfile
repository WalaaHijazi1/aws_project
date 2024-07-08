#FROM ubuntu:latest
FROM python:3.8
LABEL authors="Daniel"
#this is a docker build file to make the app run on linux ubuntu or python container
#commming version will include ngrok with ubuntu image

#install some additinal apps
RUN apt update && \
    apt install -y nano && \
    apt install -y vim
    #apt install -y python3 && \
    #apt install -y pip

#Working Directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8443

CMD ["python3", "app.py"]
