"""人脸匹配事件 ORM 模型（face_match_events 表）。"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class FaceMatchEventORM(Base):
    __tablename__ = "face_match_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    deployment_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    face_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    face_profile_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    face_profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    snapshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    camera_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    camera_area: Mapped[str | None] = mapped_column(String(64), nullable=True)

    similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_face_match_events_task_matched", FaceMatchEventORM.deployment_task_id, FaceMatchEventORM.matched_at)
