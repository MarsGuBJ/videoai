"""复核任务 ORM 模型（review_tasks 表）。

复核任务记录一次「上传图片 + 复核类型 + 大模型配置」的判定过程，
复核类型与大模型配置的 name/code 以快照形式冗余存储，避免事后改配置影响历史记录。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class ReviewTaskORM(Base):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_type_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # 复核类型快照（创建时冗余，历史记录不随类型改名而变化）
    review_type_name: Mapped[str] = mapped_column(String(200), nullable=False)
    review_type_code: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_config_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # 大模型配置名称快照
    llm_config_name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    # 进行中 / 已完成 / 失败
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="进行中")
    # 有效 / 无效 / 空串（未判定）
    verdict: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
