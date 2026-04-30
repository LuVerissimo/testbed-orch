from datetime import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class JobCreate(BaseModel):
    device_id: str
    config: dict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: str
    status: str
    config: dict
    created_at: datetime
