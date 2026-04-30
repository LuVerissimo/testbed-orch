from test_manager.generated import asset_manager_pb2, asset_manager_pb2_grpc
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .schemas import JobCreate, JobResponse
from .models import TestJobs
from uuid import UUID
import grpc
from enqueue import enqueue_job

app = FastAPI()
_channel = grpc.insecure_channel("asset-manager:50051")
_stub = asset_manager_pb2_grpc.DeviceServiceStub(_channel)


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def read_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(TestJobs, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not job by that ID"
        )
    return job


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    try:
        reservation = _stub.ReserveDevice(
            asset_manager_pb2.ReserveDeviceRequest(
                device_id=payload.device_id,
                reserved_by="test-manager",
                duration_seconds=3600,
            )
        )

    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            raise HTTPException(status_code=409, detail="Device already reserved")
        raise HTTPException(status_code=502)

    job = TestJobs(
        device_id=payload.device_id,
        config=payload.config,
        reservation_id=reservation.reservation.reservation_id,
    )

    db.add(job)

    await db.commit()
    await db.refresh(job)
    await enqueue_job(job.id)
    return job


@app.delete("/jobs/{job_id}", status_code=204)
async def update_job(job_id: str, db: AsyncSession = Depends(get_db)):

    job = await db.get(TestJobs, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        _stub.ReleaseDevice(
            asset_manager_pb2.ReleaseDeviceRequest(
                reservation_id=job.reservation_id, device_id=job.device_id
            )
        )

    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Reservation not found")
        raise HTTPException(status_code=502)

    await db.delete(job)

    await db.commit()
