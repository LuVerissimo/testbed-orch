#!/bin/bash
awslocal dynamodb create-table \
  --table-name device-reservations \
  --attribute-definitions AttributeName=deviceId,AttributeType=S AttributeName=reservationId,AttributeType=S \
  --key-schema AttributeName=deviceId,KeyType=HASH AttributeName=reservationId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST