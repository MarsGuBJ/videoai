"""事件推送任务 CRUD 路由。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.event_push_task import PushTaskCreate, PushTaskOut, PushTaskUpdate
from app.services.event_push_tasks import (
    delete_push_task_from_db,
    persist_push_task,
    push_task_out,
    require_push_task,
)

router = APIRouter()


@router.get("/api/event-push-tasks", response_model=list[PushTaskOut])
def list_push_tasks() -> list[PushTaskOut]:
    """按创建时间倒序返回全部推送任务（mqPass 掩码，token 明文）。"""
    records = sorted(state.event_push_tasks_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [push_task_out(record) for record in records]


@router.post("/api/event-push-tasks", response_model=PushTaskOut)
def create_push_task(request: PushTaskCreate) -> PushTaskOut:
    """创建推送任务：生成 uuid，入内存并落库。"""
    task_id = str(uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "id": task_id,
        "name": request.name,
        "type": request.type,
        "address": request.address,
        "mq_addr": request.mqAddr,
        "mq_user": request.mqUser,
        "mq_pass": request.mqPass or "",
        "token": request.token,
        "expire_days": request.expireDays,
        "event_source": request.eventSource,
        "event_types": request.eventTypes,
        "description": request.description,
        "enabled": request.enabled,
        "created_at": now,
        "updated_at": now,
    }
    state.event_push_tasks_store[task_id] = record
    persist_push_task(record)
    return push_task_out(record)


@router.put("/api/event-push-tasks/{task_id}", response_model=PushTaskOut)
def update_push_task(task_id: str, request: PushTaskUpdate) -> PushTaskOut:
    """更新推送任务；mqPass 传空字符串/None 时保留原值。"""
    record = require_push_task(task_id)
    if request.name is not None:
        record["name"] = request.name
    if request.type is not None:
        record["type"] = request.type
    if request.address is not None:
        record["address"] = request.address
    if request.mqAddr is not None:
        record["mq_addr"] = request.mqAddr
    if request.mqUser is not None:
        record["mq_user"] = request.mqUser
    if request.mqPass:
        record["mq_pass"] = request.mqPass
    if request.token is not None:
        record["token"] = request.token
    if request.expireDays is not None:
        record["expire_days"] = request.expireDays
    if request.eventSource is not None:
        record["event_source"] = request.eventSource
    if request.eventTypes is not None:
        record["event_types"] = request.eventTypes
    if request.description is not None:
        record["description"] = request.description
    if request.enabled is not None:
        record["enabled"] = request.enabled
    record["updated_at"] = datetime.now(timezone.utc)
    persist_push_task(record)
    return push_task_out(record)


@router.delete("/api/event-push-tasks/{task_id}")
def delete_push_task(task_id: str) -> dict[str, str]:
    """删除推送任务：移出内存并删库。"""
    record = state.event_push_tasks_store.pop(task_id, None)
    if not record:
        raise HTTPException(status_code=404, detail="Push task not found")
    delete_push_task_from_db(task_id)
    return {"deleted": task_id}
