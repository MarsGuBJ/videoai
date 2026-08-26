"""事件推送任务的内存态与数据库持久化。"""

import logging
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.event_push_task import EventPushTaskORM
from app.schemas.event_push_task import PushTaskOut

logger = logging.getLogger(__name__)


def require_push_task(task_id: str) -> dict[str, Any]:
    """按 ID 取推送任务，不存在则 404。

    Args:
        task_id: 推送任务 ID。

    Returns:
        内存态中的推送任务字典。

    Raises:
        HTTPException: 推送任务不存在时 404。
    """
    record = state.event_push_tasks_store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Push task not found")
    return record


def mask_mq_pass(mq_pass: str) -> str:
    """mqPass 掩码：仅保留前 3 字符 + "***"（空串原样返回）。

    Args:
        mq_pass: 明文 MQ 密码。

    Returns:
        掩码后的字符串。
    """
    if not mq_pass:
        return ""
    return mq_pass[:3] + "***"


def push_task_out(record: dict[str, Any]) -> PushTaskOut:
    """把内存态推送任务字典转为对外 DTO（mqPass 掩码，token 明文）。

    Args:
        record: 内存态推送任务字典。

    Returns:
        camelCase 对外 DTO。
    """
    mq_pass = str(record.get("mq_pass") or "")
    return PushTaskOut(
        id=str(record["id"]),
        name=str(record["name"]),
        type=str(record["type"]),  # type: ignore[arg-type]
        address=str(record.get("address") or ""),
        mqAddr=str(record.get("mq_addr") or ""),
        mqUser=str(record.get("mq_user") or ""),
        mqPass=mask_mq_pass(mq_pass),
        mqPassConfigured=bool(mq_pass),
        token=str(record.get("token") or ""),
        expireDays=int(record.get("expire_days") or 30),
        eventSource=str(record.get("event_source") or ""),
        eventTypes=str(record.get("event_types") or ""),
        description=str(record.get("description") or ""),
        enabled=bool(record.get("enabled", True)),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_push_task_schema() -> None:
    """轻量迁移：确保 event_push_tasks 表存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, EventPushTaskORM.__table__).create(conn, checkfirst=True)
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("push task schema ensure failed: %s", exc)


def load_push_tasks_from_db() -> None:
    """启动时把数据库中的推送任务载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(EventPushTaskORM).all()
            state.event_push_tasks_store.clear()
            for row in rows:
                state.event_push_tasks_store[str(row.id)] = {
                    "id": str(row.id),
                    "name": row.name,
                    "type": row.type,
                    "address": row.address or "",
                    "mq_addr": row.mq_addr or "",
                    "mq_user": row.mq_user or "",
                    "mq_pass": row.mq_pass or "",
                    "token": row.token or "",
                    "expire_days": int(row.expire_days or 30),
                    "event_source": row.event_source or "",
                    "event_types": row.event_types or "",
                    "description": row.description or "",
                    "enabled": bool(row.enabled),
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空任务集启动（与布控任务一致）
        logger.error("push task load failed: %s", exc)


def persist_push_task(record: dict[str, Any]) -> None:
    """把推送任务 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的推送任务字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(EventPushTaskORM, str(record["id"]))
            if row is None:
                row = EventPushTaskORM(id=str(record["id"]))
                pgdb.add(row)
            row.name = str(record["name"])
            row.type = str(record["type"])
            row.address = str(record.get("address") or "")
            row.mq_addr = str(record.get("mq_addr") or "")
            row.mq_user = str(record.get("mq_user") or "")
            row.mq_pass = str(record.get("mq_pass") or "")
            row.token = str(record.get("token") or "")
            row.expire_days = int(record.get("expire_days") or 30)
            row.event_source = str(record.get("event_source") or "")
            row.event_types = str(record.get("event_types") or "")
            row.description = str(record.get("description") or "")
            row.enabled = bool(record.get("enabled", True))
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("push task persist failed: %s", exc)


def delete_push_task_from_db(task_id: str) -> None:
    """从数据库删除推送任务；失败仅记录日志。

    Args:
        task_id: 推送任务 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(EventPushTaskORM, task_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("push task delete failed: %s", exc)
