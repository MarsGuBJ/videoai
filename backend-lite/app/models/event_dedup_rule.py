"""事件去重规则 ORM 模型（event_dedup_rules 表）。"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class EventDedupRuleORM(Base):
    __tablename__ = "event_dedup_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="时间维度去重")
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    all_cameras: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cameras: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    remark: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
