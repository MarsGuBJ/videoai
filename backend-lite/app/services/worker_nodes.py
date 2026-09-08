"""Worker 节点注册表：内存态与数据库持久化。"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import Table, text
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models.worker_node import WorkerNodeORM
from app.schemas.worker_node import GpuOut, SystemMetricIn, WorkerHeartbeatIn, WorkerNodeOut

logger = logging.getLogger(__name__)

GPU_BUSY_UTILIZATION_PCT = 50


def _as_aware(value: datetime) -> datetime:
    """数据库读回的 datetime 可能不带时区，统一按 UTC 处理以便与 now 比较。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def ensure_worker_node_schema() -> None:
    """轻量迁移：确保 worker_nodes 表及后增列存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, WorkerNodeORM.__table__).create(conn, checkfirst=True)
            conn.execute(text("ALTER TABLE worker_nodes ADD COLUMN IF NOT EXISTS system TEXT NOT NULL DEFAULT '{}'"))
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("worker node schema ensure failed: %s", exc)


def load_worker_nodes_from_db() -> None:
    """启动时把数据库中的 worker 节点载入内存存储（gpus 反序列化 JSON）。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(WorkerNodeORM).all()
            state.worker_nodes_store.clear()
            for row in rows:
                state.worker_nodes_store[str(row.id)] = {
                    "id": str(row.id),
                    "hostname": row.hostname,
                    "ip": row.ip or "",
                    "port": row.port or 0,
                    "gpus": json.loads(row.gpus or "[]"),
                    "system": json.loads(row.system or "{}"),
                    "last_seen_at": row.last_seen_at,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空节点集启动（与复核类型一致）
        logger.error("worker node load failed: %s", exc)


def persist_worker_node(record: dict[str, Any]) -> None:
    """把 worker 节点 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的 worker 节点字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(WorkerNodeORM, str(record["id"]))
            if row is None:
                row = WorkerNodeORM(id=str(record["id"]))
                pgdb.add(row)
            row.hostname = str(record["hostname"])
            row.ip = str(record.get("ip") or "")
            row.port = int(record.get("port") or 0)
            row.gpus = json.dumps(record.get("gpus") or [], ensure_ascii=False)
            row.system = json.dumps(record.get("system") or {}, ensure_ascii=False)
            row.last_seen_at = _as_aware(record["last_seen_at"])
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("worker node persist failed: %s", exc)


def worker_node_out(record: dict[str, Any]) -> WorkerNodeOut:
    """把内存态 worker 节点字典转为对外 DTO（在线状态与 GPU 状态按契约派生）。

    Args:
        record: 内存态 worker 节点字典。

    Returns:
        camelCase 对外 DTO。
    """
    now = datetime.now(timezone.utc)
    last_seen_at = _as_aware(record["last_seen_at"])
    online = (now - last_seen_at).total_seconds() <= get_settings().worker_node_offline_seconds
    gpus = [
        GpuOut(
            **gpu,
            status=(
                "离线"
                if not online
                else ("繁忙" if int(gpu.get("utilizationPct", 0)) >= GPU_BUSY_UTILIZATION_PCT else "空闲")
            ),
        )
        for gpu in record.get("gpus", [])
    ]
    return WorkerNodeOut(
        id=str(record["id"]),
        hostname=str(record["hostname"]),
        ip=str(record.get("ip") or ""),
        port=int(record.get("port") or 0),
        status="在线" if online else "离线",
        lastSeenAt=last_seen_at,
        gpus=gpus,
        system=SystemMetricIn(**(record.get("system") or {})),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def record_worker_heartbeat(payload: WorkerHeartbeatIn) -> dict[str, Any]:
    """处理 worker 心跳：按 hostname upsert 内存态（保留 created_at）并落库。

    Args:
        payload: 心跳请求体。

    Returns:
        更新后的内存态 worker 节点字典。
    """
    now = datetime.now(timezone.utc)
    record = state.worker_nodes_store.get(payload.hostname)
    if record is None:
        record = {
            "id": payload.hostname,
            "hostname": payload.hostname,
            "ip": payload.ip,
            "port": payload.port,
            "gpus": [],
            "system": {},
            "last_seen_at": now,
            "created_at": now,
            "updated_at": now,
        }
        state.worker_nodes_store[payload.hostname] = record
    if payload.ip:  # 心跳 IP 为空时保留旧值
        record["ip"] = payload.ip
    record["port"] = payload.port
    record["gpus"] = [metric.model_dump() for metric in payload.gpus]
    record["system"] = payload.system.model_dump()
    record["last_seen_at"] = now
    record["updated_at"] = now
    persist_worker_node(record)
    return record
