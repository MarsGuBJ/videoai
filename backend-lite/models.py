import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class CameraORM(Base):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    stream_app: Mapped[str] = mapped_column(String(64), nullable=False, default="live")
    stream_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    playback_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    nvr_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nvr_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nvr_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nvr_stream_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


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

    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


Index("ix_face_match_events_task_matched", FaceMatchEventORM.deployment_task_id, FaceMatchEventORM.matched_at)
