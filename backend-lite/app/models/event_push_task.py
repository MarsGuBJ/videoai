"""事件推送任务 ORM 模型（event_push_tasks 表）。"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class EventPushTaskORM(Base):
    __tablename__ = "event_push_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="http")
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    mq_addr: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    mq_user: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    mq_pass: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    token: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    expire_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    event_source: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    event_types: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
