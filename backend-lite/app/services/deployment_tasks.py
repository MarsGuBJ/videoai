"""布控任务的内存态与数据库持久化。"""

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.deployment_task import DeploymentTaskORM
from app.schemas.deployment_task import DEFAULT_RECOGNITION_PER_MINUTE, DeploymentTaskResponse

logger = logging.getLogger(__name__)


def clean_optional(value: str | None) -> str | None:
    """把空白字符串归一为 None。

    Args:
        value: 原始字符串，可为 None。

    Returns:
        strip 后的非空字符串，否则 None。
    """
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def require_deployment_task(task_id: UUID) -> DeploymentTaskResponse:
    """按 ID 取布控任务，不存在则 404。

    Args:
        task_id: 任务 ID。

    Returns:
        对应的布控任务。

    Raises:
        HTTPException: 任务不存在时 404。
    """
    task = state.deployment_tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Deployment task not found")
    return task


def ensure_deployment_task_schema() -> None:
    """轻量迁移：为 deployment_tasks 补 recognition_per_minute 列（幂等）。"""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE deployment_tasks "
                    "ADD COLUMN IF NOT EXISTS recognition_per_minute INTEGER NOT NULL DEFAULT 60"
                )
            )
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("deployment task schema ensure failed: %s", exc)


def load_deployment_tasks_from_db() -> None:
    """启动时把数据库中的布控任务载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(DeploymentTaskORM).all()
            state.deployment_tasks_store.clear()
            for row in rows:
                state.deployment_tasks_store[row.id] = DeploymentTaskResponse(
                    id=row.id,
                    name=row.name,
                    pipeline=row.pipeline,
                    area=row.area,
                    areaCount=int(row.area_count or 0),
                    enabled=bool(row.enabled),
                    taskStatus=row.task_status,
                    desc=row.desc or "",
                    faceProfileId=row.face_profile_id,
                    faceProfileName=row.face_profile_name,
                    faceProfilePhotoUrl=row.face_profile_photo_url,
                    cameraIds=list(row.camera_ids or []),
                    recognitionPerMinute=max(1, int(row.recognition_per_minute or DEFAULT_RECOGNITION_PER_MINUTE)),
                    createdAt=row.created_at,
                    updatedAt=row.updated_at,
                )
    except SQLAlchemyError as exc:  # 数据库不可达时以空任务集启动（与原逻辑一致）
        logger.error("deployment task load failed: %s", exc)


def persist_deployment_task(task: DeploymentTaskResponse) -> None:
    """把任务 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        task: 待持久化的任务。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(DeploymentTaskORM, task.id)
            if row is None:
                row = DeploymentTaskORM(id=task.id)
                pgdb.add(row)
            row.name = task.name
            row.pipeline = task.pipeline
            row.area = task.area
            row.area_count = task.areaCount
            row.enabled = task.enabled
            row.desc = task.desc
            row.task_status = task.taskStatus
            row.face_profile_id = task.faceProfileId
            row.face_profile_name = task.faceProfileName
            row.face_profile_photo_url = task.faceProfilePhotoUrl
            row.camera_ids = list(task.cameraIds or [])
            row.recognition_per_minute = max(1, int(task.recognitionPerMinute or DEFAULT_RECOGNITION_PER_MINUTE))
            row.created_at = task.createdAt
            row.updated_at = task.updatedAt
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("deployment task persist failed: %s", exc)


def delete_deployment_task_from_db(task_id: UUID) -> None:
    """从数据库删除任务；失败仅记录日志。

    Args:
        task_id: 任务 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(DeploymentTaskORM, task_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("deployment task delete failed: %s", exc)
