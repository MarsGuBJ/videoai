"""复核任务的内存态、数据库持久化与大模型判定执行。"""

import logging
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.review_task import ReviewTaskORM
from app.schemas.review_task import ReviewTaskOut
from app.services import llm_client

logger = logging.getLogger(__name__)

MAX_ERROR_REASON_CHARS = 500


def require_review_task(task_id: str) -> dict[str, Any]:
    """按 ID 取复核任务，不存在则 404。

    Args:
        task_id: 复核任务 ID。

    Returns:
        内存态中的复核任务字典。

    Raises:
        HTTPException: 复核任务不存在时 404。
    """
    record = state.review_tasks_store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Review task not found")
    return record


def review_task_out(record: dict[str, Any]) -> ReviewTaskOut:
    """把内存态复核任务字典转为对外 DTO。

    Args:
        record: 内存态复核任务字典。

    Returns:
        camelCase 对外 DTO。
    """
    return ReviewTaskOut(
        id=str(record["id"]),
        reviewTypeId=str(record["review_type_id"]),
        reviewTypeName=str(record["review_type_name"]),
        reviewTypeCode=str(record["review_type_code"]),
        llmConfigId=str(record["llm_config_id"]),
        llmConfigName=str(record["llm_config_name"]),
        imageUrl=str(record["image_url"]),
        status=str(record["status"]),
        verdict=str(record.get("verdict") or ""),
        reason=str(record.get("reason") or ""),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_review_task_schema() -> None:
    """轻量迁移：确保 review_tasks 表存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, ReviewTaskORM.__table__).create(conn, checkfirst=True)
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("review task schema ensure failed: %s", exc)


def load_review_tasks_from_db() -> None:
    """启动时把数据库中的复核任务载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(ReviewTaskORM).all()
            state.review_tasks_store.clear()
            for row in rows:
                state.review_tasks_store[str(row.id)] = {
                    "id": str(row.id),
                    "review_type_id": row.review_type_id,
                    "review_type_name": row.review_type_name,
                    "review_type_code": row.review_type_code,
                    "llm_config_id": row.llm_config_id,
                    "llm_config_name": row.llm_config_name,
                    "image_url": row.image_url,
                    "status": row.status,
                    "verdict": row.verdict or "",
                    "reason": row.reason or "",
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空任务集启动（与复核类型一致）
        logger.error("review task load failed: %s", exc)


def persist_review_task(record: dict[str, Any]) -> None:
    """把复核任务 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的复核任务字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(ReviewTaskORM, str(record["id"]))
            if row is None:
                row = ReviewTaskORM(id=str(record["id"]))
                pgdb.add(row)
            row.review_type_id = str(record["review_type_id"])
            row.review_type_name = str(record["review_type_name"])
            row.review_type_code = str(record["review_type_code"])
            row.llm_config_id = str(record["llm_config_id"])
            row.llm_config_name = str(record["llm_config_name"])
            row.image_url = str(record["image_url"])
            row.status = str(record["status"])
            row.verdict = str(record.get("verdict") or "")
            row.reason = str(record.get("reason") or "")
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("review task persist failed: %s", exc)


def delete_review_task_from_db(task_id: str) -> None:
    """从数据库删除复核任务；失败仅记录日志。

    Args:
        task_id: 复核任务 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(ReviewTaskORM, task_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("review task delete failed: %s", exc)


def run_review_task_judgment(task_id: str, image_bytes: bytes) -> None:
    """执行复核任务的大模型判定并更新内存态与数据库（后台线程调用，永不抛异常）。

    Args:
        task_id: 复核任务 ID。
        image_bytes: 待判定图片字节。
    """
    try:
        record = state.review_tasks_store.get(task_id)
        if not record:
            logger.error("review task judgment skipped, task not found: %s", task_id)
            return
        review_type = state.review_types_store.get(str(record["review_type_id"]))
        if not review_type:
            raise ValueError(f"review type not found: {record['review_type_id']}")
        llm_cfg = state.llm_configs_store.get(str(record["llm_config_id"]))
        if not llm_cfg:
            raise ValueError(f"llm config not found: {record['llm_config_id']}")
        verdict, reason = llm_client.judge_event(
            base_url=str(llm_cfg["base_url"]),
            api_key=str(llm_cfg.get("api_key") or ""),
            model=llm_cfg.get("model"),
            prompt=str(review_type["prompt"]),
            image_bytes=image_bytes,
            timeout=int(llm_cfg.get("timeout") or 30),
            temperature=float(llm_cfg.get("temperature") or 0.0),
            max_tokens=int(llm_cfg.get("max_tokens") or 1024),
        )
        record["status"] = "已完成"
        record["verdict"] = verdict
        record["reason"] = reason
    except Exception as exc:  # noqa: BLE001  # 后台线程内任何失败都落为任务失败状态
        logger.error("review task judgment failed: %s", exc)
        record = state.review_tasks_store.get(task_id)
        if record is None:
            return
        record["status"] = "失败"
        record["reason"] = str(exc)[:MAX_ERROR_REASON_CHARS]
    record["updated_at"] = datetime.now(timezone.utc)
    persist_review_task(record)
