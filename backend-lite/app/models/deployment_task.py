"""布控任务 ORM 模型（deployment_tasks 表）。"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class DeploymentTaskORM(Base):
    __tablename__ = "deployment_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    pipeline: Mapped[str] = mapped_column(String(64), nullable=False, default="人脸识别流程")
    area: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    area_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    task_status: Mapped[str] = mapped_column(String(32), nullable=False, default="stopped")

    face_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    face_profile_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    face_profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    camera_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    recognition_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
