#!/bin/bash

echo "==> Creating Dynamo tables..."

awslocal dynamodb create-table \
  --table-name device-reservations \
  --attribute-definitions AttributeName=deviceId,AttributeType=S AttributeName=reservationId,AttributeType=S \
  --key-schema AttributeName=deviceId,KeyType=HASH AttributeName=reservationId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

echo "==> Creating SQS queues..."

awslocal sqs create-queue \
  --queue-name test-jobs \
  --region "${DEFAULT_REGION:-us-east-1}"

echo "==> SQS queues ready."