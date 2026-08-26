"""事件去重规则的内存态与数据库持久化。"""

import logging
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.event_dedup_rule import EventDedupRuleORM
from app.schemas.event_dedup_rule import DedupRuleOut

logger = logging.getLogger(__name__)


def require_dedup_rule(rule_id: str) -> dict[str, Any]:
    """按 ID 取去重规则，不存在则 404。

    Args:
        rule_id: 去重规则 ID。

    Returns:
        内存态中的去重规则字典。

    Raises:
        HTTPException: 去重规则不存在时 404。
    """
    record = state.event_dedup_rules_store.get(rule_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dedup rule not found")
    return record


def dedup_rule_out(record: dict[str, Any]) -> DedupRuleOut:
    """把内存态去重规则字典转为对外 DTO。

    Args:
        record: 内存态去重规则字典。

    Returns:
        camelCase 对外 DTO。
    """
    duration = record.get("duration_minutes")
    similarity = record.get("similarity")
    return DedupRuleOut(
        id=str(record["id"]),
        name=str(record["name"]),
        algorithm=str(record.get("algorithm") or ""),
        strategy=str(record["strategy"]),  # type: ignore[arg-type]
        durationMinutes=int(duration) if duration is not None else None,
        similarity=float(similarity) if similarity is not None else None,
        allCameras=bool(record.get("all_cameras", True)),
        cameras=[str(item) for item in (record.get("cameras") or [])],
        remark=str(record.get("remark") or ""),
        enabled=bool(record.get("enabled", True)),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_dedup_rule_schema() -> None:
    """轻量迁移：确保 event_dedup_rules 表存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, EventDedupRuleORM.__table__).create(conn, checkfirst=True)
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("dedup rule schema ensure failed: %s", exc)


def load_dedup_rules_from_db() -> None:
    """启动时把数据库中的去重规则载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(EventDedupRuleORM).all()
            state.event_dedup_rules_store.clear()
            for row in rows:
                state.event_dedup_rules_store[str(row.id)] = {
                    "id": str(row.id),
                    "name": row.name,
                    "algorithm": row.algorithm or "",
                    "strategy": row.strategy,
                    "duration_minutes": row.duration_minutes,
                    "similarity": row.similarity,
                    "all_cameras": bool(row.all_cameras),
                    "cameras": row.cameras or [],
                    "remark": row.remark or "",
                    "enabled": bool(row.enabled),
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空规则集启动（与布控任务一致）
        logger.error("dedup rule load failed: %s", exc)


def persist_dedup_rule(record: dict[str, Any]) -> None:
    """把去重规则 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的去重规则字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(EventDedupRuleORM, str(record["id"]))
            if row is None:
                row = EventDedupRuleORM(id=str(record["id"]))
                pgdb.add(row)
            row.name = str(record["name"])
            row.algorithm = str(record.get("algorithm") or "")
            row.strategy = str(record["strategy"])
            duration = record.get("duration_minutes")
            similarity = record.get("similarity")
            row.duration_minutes = int(duration) if duration is not None else None
            row.similarity = float(similarity) if similarity is not None else None
            row.all_cameras = bool(record.get("all_cameras", True))
            row.cameras = [str(item) for item in (record.get("cameras") or [])]
            row.remark = str(record.get("remark") or "")
            row.enabled = bool(record.get("enabled", True))
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("dedup rule persist failed: %s", exc)


def delete_dedup_rule_from_db(rule_id: str) -> None:
    """从数据库删除去重规则；失败仅记录日志。

    Args:
        rule_id: 去重规则 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(EventDedupRuleORM, rule_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("dedup rule delete failed: %s", exc)
