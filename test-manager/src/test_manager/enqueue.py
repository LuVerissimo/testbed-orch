import boto3, os, json
from uuid import UUID

sqs = boto3.client(
    "sqs",
    endpoint_url=os.environ.get("SQS_ENDPOINT_URL"),
)
queue_url = os.environ.get("SQS_QUEUE_URL")


def enqueue_job(job_id: UUID) -> None:
    sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=20,
        MessageBody=json.dumps({"job_id": str(job_id)}),
    )
