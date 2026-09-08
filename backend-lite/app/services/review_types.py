"""复核类型的内存态与数据库持久化。"""

import logging
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import Table, text
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.review_type import ReviewTypeORM
from app.schemas.review_type import ReviewTypeOut

logger = logging.getLogger(__name__)


def require_review_type(type_id: str) -> dict[str, Any]:
    """按 ID 取复核类型，不存在则 404。

    Args:
        type_id: 复核类型 ID。

    Returns:
        内存态中的复核类型字典。

    Raises:
        HTTPException: 复核类型不存在时 404。
    """
    record = state.review_types_store.get(type_id)
    if not record:
        raise HTTPException(status_code=404, detail="Review type not found")
    return record


def review_type_out(record: dict[str, Any]) -> ReviewTypeOut:
    """把内存态复核类型字典转为对外 DTO。

    Args:
        record: 内存态复核类型字典。

    Returns:
        camelCase 对外 DTO。
    """
    return ReviewTypeOut(
        id=str(record["id"]),
        name=str(record["name"]),
        code=str(record["code"]),
        prompt=str(record["prompt"]),
        injectEvent=str(record.get("inject_event") or ""),
        remark=str(record.get("remark") or ""),
        llmConfigId=record.get("llm_config_id"),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_review_type_schema() -> None:
    """轻量迁移：确保 review_types 表存在并补列（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, ReviewTypeORM.__table__).create(conn, checkfirst=True)
            conn.execute(
                text("ALTER TABLE review_types ADD COLUMN IF NOT EXISTS llm_config_id VARCHAR(36)")
            )
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("review type schema ensure failed: %s", exc)


def load_review_types_from_db() -> None:
    """启动时把数据库中的复核类型载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(ReviewTypeORM).all()
            state.review_types_store.clear()
            for row in rows:
                state.review_types_store[str(row.id)] = {
                    "id": str(row.id),
                    "name": row.name,
                    "code": row.code,
                    "prompt": row.prompt,
                    "inject_event": row.inject_event or "",
                    "remark": row.remark or "",
                    "llm_config_id": row.llm_config_id,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空配置集启动（与大模型配置一致）
        logger.error("review type load failed: %s", exc)


def persist_review_type(record: dict[str, Any]) -> None:
    """把复核类型 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的复核类型字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(ReviewTypeORM, str(record["id"]))
            if row is None:
                row = ReviewTypeORM(id=str(record["id"]))
                pgdb.add(row)
            row.name = str(record["name"])
            row.code = str(record["code"])
            row.prompt = str(record["prompt"])
            row.inject_event = str(record.get("inject_event") or "")
            row.remark = str(record.get("remark") or "")
            row.llm_config_id = record.get("llm_config_id")
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("review type persist failed: %s", exc)


def delete_review_type_from_db(type_id: str) -> None:
    """从数据库删除复核类型；失败仅记录日志。

    Args:
        type_id: 复核类型 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(ReviewTypeORM, type_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("review type delete failed: %s", exc)
