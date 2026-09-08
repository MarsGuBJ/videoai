"""布控任务事件 ORM 模型（deployment_events 表）。

统一存储布控任务产生的全部事件：人脸比对命中与算法目标检测事件。
event_type 区分事件类别，deployment_task_id 标识来源布控任务。
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, utcnow


class DeploymentEventORM(Base):
    __tablename__ = "deployment_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    deployment_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 事件类别：face_match / object_detection（或 worker 上报的 eventType）
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 算法编号（来自布控任务快照）
    algorithm_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 复核状态：空/有效/无效
    review_status: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # 人脸比对事件字段
    face_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    face_profile_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    face_profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 目标检测事件字段（objects 为 ObjectInfo 字典列表）
    objects: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    frame_width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frame_height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    snapshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 快照感知哈希（图像去重策略使用）
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    camera_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    camera_area: Mapped[str | None] = mapped_column(String(64), nullable=True)

    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 事件在视频中的发生时间
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_deployment_events_task_occurred", DeploymentEventORM.deployment_task_id, DeploymentEventORM.occurred_at)
Index("ix_deployment_events_camera_occurred", DeploymentEventORM.camera_id, DeploymentEventORM.occurred_at)
