"""Worker 节点注册表 ORM 模型（worker_nodes 表）。

worker 周期心跳上报主机信息与 GPU 指标，节点以 hostname 为主键幂等 upsert，
gpus 为 JSON 序列化的 GpuMetric 列表（结构与心跳契约一致）。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class WorkerNodeORM(Base):
    __tablename__ = "worker_nodes"

    id: Mapped[str] = mapped_column(String(200), primary_key=True)  # = hostname
    hostname: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # JSON 序列化的 GpuMetric 列表
    gpus: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON 序列化的系统指标（CPU/内存/磁盘，结构与心跳契约 SystemMetricIn 一致）
    system: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
