import asyncio, boto3, json, logging, os, time
import paramiko, grpc
from sqlalchemy import update
from test_manager.generated import asset_manager_pb2, asset_manager_pb2_grpc
from .database import AsyncSessionLocal
from .models import TestJobs, TestResults

log = logging.getLogger(__name__)

sqs = boto3.client("sqs", endpoint_url=os.environ.get("SQS_ENDPOINT_URL"))
queue_url = os.environ.get("SQS_QUEUE_URL")

_channel = grpc.insecure_channel(
    f"{os.environ.get('ASSET_MANAGER_GRPC_HOST', 'asset-manager')}:"
    f"{os.environ.get('ASSET_MANAGER_GRPC_PORT', '50051')}"
)
_stub = asset_manager_pb2_grpc.DeviceServiceStub(_channel)


async def poll() -> None:
    log.info("Worker started, polling %s", queue_url)
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=20,
        )
        for msg in response.get("Messages", []):
            await process_job(msg)


async def process_job(msg: dict) -> None:
    receipt = msg["ReceiptHandle"]
    job_id = json.loads(msg["Body"])["job_id"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(TestJobs)
            .where(TestJobs.id == job_id, TestJobs.status == "pending")
            .values(status="running")
        )
        await db.commit()

        if result.rowcount == 0:
            _delete_message(receipt)
            return

        job = await db.get(TestJobs, job_id)

        stdout, stderr, exit_code, duration_ms = "", "", -1, 0
        try:
            stdout, stderr, exit_code, duration_ms = _run_ssh(job)
        except Exception as e:
            log.error("SSH failed for job %s: %s", job_id, e)
            stderr = str(e)

        db.add(
            TestResults(
                job_id=job.id,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
            )
        )
        await db.execute(
            update(TestJobs)
            .where(TestJobs.id == job_id)
            .values(status="completed" if exit_code == 0 else "failed")
        )
        await db.commit()

    try:
        _stub.ReleaseDevice(
            asset_manager_pb2.ReleaseDeviceRequest(
                device_id=job.device_id,
                reservation_id=job.reservation_id,
            )
        )
    except grpc.RpcError as e:
        log.error("ReleaseDevice failed for job %s: %s", job_id, e)

    _delete_message(receipt)


def _run_ssh(job: TestJobs) -> tuple[str, str, int, int]:
    cfg = job.config
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=cfg["hostname"],
            username=cfg["username"],
            password=cfg.get("password"),
        )
        start = time.monotonic()
        _, stdout, stderr = client.exec_command(cfg.get("command", "true"))
        exit_code = stdout.channel.recv_exit_status()
        duration_ms = int((time.monotonic() - start) * 1000)
        return stdout.read().decode(), stderr.read().decode(), exit_code, duration_ms
    finally:
        client.close()


def _delete_message(receipt: str) -> None:
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)


if __name__ == "__main__":
    asyncio.run(poll())
