"""事件信息 ORM 模型（event_infos 表）。"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class EventInfoORM(Base):
    __tablename__ = "event_infos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="低")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    mark: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    icon_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    event_source: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    algorithm_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    attrs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
