"""事件信息的内存态与数据库持久化。"""

import logging
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.event_info import EventInfoORM
from app.schemas.event_info import EventInfoOut

logger = logging.getLogger(__name__)


def require_event_info(event_id: str) -> dict[str, Any]:
    """按 ID 取事件信息，不存在则 404。

    Args:
        event_id: 事件信息 ID。

    Returns:
        内存态中的事件信息字典。

    Raises:
        HTTPException: 事件信息不存在时 404。
    """
    record = state.event_infos_store.get(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event info not found")
    return record


def event_info_out(record: dict[str, Any]) -> EventInfoOut:
    """把内存态事件信息字典转为对外 DTO。

    Args:
        record: 内存态事件信息字典。

    Returns:
        camelCase 对外 DTO。
    """
    return EventInfoOut(
        id=str(record["id"]),
        name=str(record["name"]),
        code=str(record["code"]),
        level=str(record["level"]),  # type: ignore[arg-type]
        category=str(record.get("category") or ""),
        mark=str(record.get("mark") or ""),
        iconName=str(record.get("icon_name") or ""),
        source=str(record.get("source") or ""),
        eventSource=str(record.get("event_source") or ""),
        algorithmCode=str(record.get("algorithm_code") or ""),
        attrs=record.get("attrs") or [],
        sortOrder=int(record.get("sort_order") or 0),
        enabled=bool(record.get("enabled", True)),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_event_info_schema() -> None:
    """轻量迁移：确保 event_infos 表存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, EventInfoORM.__table__).create(conn, checkfirst=True)
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("event info schema ensure failed: %s", exc)


def load_event_infos_from_db() -> None:
    """启动时把数据库中的事件信息载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(EventInfoORM).all()
            state.event_infos_store.clear()
            for row in rows:
                state.event_infos_store[str(row.id)] = {
                    "id": str(row.id),
                    "name": row.name,
                    "code": row.code,
                    "level": row.level,
                    "category": row.category or "",
                    "mark": row.mark or "",
                    "icon_name": row.icon_name or "",
                    "source": row.source or "",
                    "event_source": row.event_source or "",
                    "algorithm_code": row.algorithm_code or "",
                    "attrs": row.attrs or [],
                    "sort_order": int(row.sort_order or 0),
                    "enabled": bool(row.enabled),
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空事件集启动（与布控任务一致）
        logger.error("event info load failed: %s", exc)


def persist_event_info(record: dict[str, Any]) -> None:
    """把事件信息 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的事件信息字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(EventInfoORM, str(record["id"]))
            if row is None:
                row = EventInfoORM(id=str(record["id"]))
                pgdb.add(row)
            row.name = str(record["name"])
            row.code = str(record["code"])
            row.level = str(record["level"])
            row.category = str(record.get("category") or "")
            row.mark = str(record.get("mark") or "")
            row.icon_name = str(record.get("icon_name") or "")
            row.source = str(record.get("source") or "")
            row.event_source = str(record.get("event_source") or "")
            row.algorithm_code = str(record.get("algorithm_code") or "")
            row.attrs = list(record.get("attrs") or [])
            row.sort_order = int(record.get("sort_order") or 0)
            row.enabled = bool(record.get("enabled", True))
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("event info persist failed: %s", exc)


def delete_event_info_from_db(event_id: str) -> None:
    """从数据库删除事件信息；失败仅记录日志。

    Args:
        event_id: 事件信息 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(EventInfoORM, event_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("event info delete failed: %s", exc)
