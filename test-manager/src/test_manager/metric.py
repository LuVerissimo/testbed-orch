import boto3, os, time, asyncio
from functools import wraps


CW_ENDPOINT = os.environ.get("CLOUDWATCH_ENDPOINT_URL")
NAMESPACE = "TestOrch/Worker"
cw = boto3.client("cloudwatch", endpoint_url=CW_ENDPOINT)


def track_job(job_name):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Track Submittals
            _put_metric(job_name, "JOBS_SUBMITTED", 1.0, "Count")

            _start_time = time.time()
            try:
                result = await `func(*args, **kwargs)
                # track completion
                _put_metric(job_name, "JOBS_COMPLETED", 1.0, "Count")
                return result
            except Exception as e:
                # track failed
                _put_metric(job_name, "JOBS_FAILED", 1.0, "Count")
                raise e
            finally:
                # track duration
                duration = time.time() - _start_time
                _put_metric(job_name, "JOBS_DURATION", duration, "Seconds")

        return wrapper

    return decorator


def _put_metric(job_name, metric_name, value, unit):
    """Helper to send data to CW"""
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": metric_name,
                "Dimensions": [
                    {"Name": "JobName", "Value": job_name},
                ],
                "Unit": unit,
                "Value": float(value),
            },
        ],
    )
