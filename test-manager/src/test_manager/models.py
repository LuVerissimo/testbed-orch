import uuid
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import String, JSONB, func, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TestJobs(Base):
    __tablename__ = "test_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(30))
    reservation_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
