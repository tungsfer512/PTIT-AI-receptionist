FROM python:3.11.7

RUN apt update
RUN apt upgrade -y

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5050
