"""定时复核任务 ORM 模型（review_schedules 表）。

定时复核任务按 cron 周期触发：批量抽取未复核的布控事件，
为每条事件创建复核任务并调用大模型判定，回写事件复核状态。
复核类型 name/code 以快照形式冗余存储，避免事后改类型影响存量调度行为。
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class ReviewScheduleORM(Base):
    __tablename__ = "review_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cron: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    review_type_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # 复核类型快照（创建/更新时冗余，历史行为不随类型改名而变化）
    review_type_name: Mapped[str] = mapped_column(String(200), nullable=False)
    review_type_code: Mapped[str] = mapped_column(String(100), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 形如「处理 12 条：有效 8 / 无效 3 / 失败 1 / 跳过 2」
    last_result: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
