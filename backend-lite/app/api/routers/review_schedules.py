"""定时复核任务 CRUD 与手动触发路由。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.review_schedule import ReviewScheduleOut, ReviewSchedulePayload
from app.services.review_schedules import (
    delete_review_schedule_from_db,
    persist_review_schedule,
    require_review_schedule,
    review_schedule_out,
    trigger_review_schedule,
    validate_cron,
)
from app.services.review_types import require_review_type

router = APIRouter()


def _validate_cron_or_422(expr: str) -> None:
    """cron 非法时返回 422（参数校验语义同 pydantic ValidationError）。

    Args:
        expr: cron 表达式。

    Raises:
        HTTPException: cron 表达式非法时 422。
    """
    try:
        validate_cron(expr)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/review-schedules", response_model=list[ReviewScheduleOut])
def list_review_schedules() -> list[ReviewScheduleOut]:
    """按创建时间倒序返回全部定时复核任务。"""
    records = sorted(state.review_schedules_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [review_schedule_out(record) for record in records]


@router.post("/api/review-schedules", response_model=ReviewScheduleOut)
def create_review_schedule(request: ReviewSchedulePayload) -> ReviewScheduleOut:
    """创建定时复核任务：复核类型必须存在，cron 必须合法，类型信息快照入库。"""
    review_type = require_review_type(request.reviewTypeId)
    _validate_cron_or_422(request.cron)
    schedule_id = str(uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "id": schedule_id,
        "name": request.name,
        "cron": request.cron,
        "enabled": request.enabled,
        "batch_size": request.batchSize,
        "review_type_id": request.reviewTypeId,
        "review_type_name": str(review_type["name"]),
        "review_type_code": str(review_type["code"]),
        "last_run_at": None,
        "last_result": "",
        "created_at": now,
        "updated_at": now,
    }
    state.review_schedules_store[schedule_id] = record
    persist_review_schedule(record)
    return review_schedule_out(record)


@router.put("/api/review-schedules/{schedule_id}", response_model=ReviewScheduleOut)
def update_review_schedule(schedule_id: str, request: ReviewSchedulePayload) -> ReviewScheduleOut:
    """更新定时复核任务：复核类型必须存在，cron 必须合法，刷新类型快照。"""
    record = require_review_schedule(schedule_id)
    review_type = require_review_type(request.reviewTypeId)
    _validate_cron_or_422(request.cron)
    record["name"] = request.name
    record["cron"] = request.cron
    record["enabled"] = request.enabled
    record["batch_size"] = request.batchSize
    record["review_type_id"] = request.reviewTypeId
    record["review_type_name"] = str(review_type["name"])
    record["review_type_code"] = str(review_type["code"])
    record["updated_at"] = datetime.now(timezone.utc)
    persist_review_schedule(record)
    return review_schedule_out(record)


@router.delete("/api/review-schedules/{schedule_id}")
def delete_review_schedule(schedule_id: str) -> dict[str, str]:
    """删除定时复核任务：移出内存并删库。"""
    record = state.review_schedules_store.pop(schedule_id, None)
    if not record:
        raise HTTPException(status_code=404, detail="Review schedule not found")
    delete_review_schedule_from_db(schedule_id)
    return {"deleted": schedule_id}


@router.post("/api/review-schedules/{schedule_id}/run")
def run_review_schedule(schedule_id: str) -> dict[str, str]:
    """手动触发一次定时复核：后台 daemon 线程异步执行，立即返回。"""
    require_review_schedule(schedule_id)
    trigger_review_schedule(schedule_id)
    return {"started": schedule_id}
