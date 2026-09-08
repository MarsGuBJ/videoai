"""复核类型 ORM 模型（review_types 表）。

复核类型用于人工复核与大模型判断的算法类型配置，
name/code 与事件信息配置中的 name/code 一一对应。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class ReviewTypeORM(Base):
    __tablename__ = "review_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    inject_event: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    remark: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # 关联的大模型配置（llm_configs.id），可为空
    llm_config_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
