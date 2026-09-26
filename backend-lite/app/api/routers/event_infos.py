"""事件信息 CRUD 路由。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from app import state
from app.schemas.event_info import EventInfoCreate, EventInfoOut, EventInfoUpdate
from app.services.event_infos import (
    assert_event_info_not_referenced,
    cascade_event_algorithm_to_tasks,
    delete_event_info_from_db,
    event_info_out,
    persist_event_info,
    require_event_info,
)

router = APIRouter()


@router.get("/api/event-infos", response_model=list[EventInfoOut])
def list_event_infos() -> list[EventInfoOut]:
    """按创建时间倒序返回全部事件信息。"""
    records = sorted(state.event_infos_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [event_info_out(record) for record in records]


@router.post("/api/event-infos", response_model=EventInfoOut)
def create_event_info(request: EventInfoCreate) -> EventInfoOut:
    """创建事件信息：生成 uuid，sortOrder 取现有最大值 +1，入内存并落库。"""
    event_id = str(uuid4())
    now = datetime.now(timezone.utc)
    sort_order = max((int(item.get("sort_order") or 0) for item in state.event_infos_store.values()), default=0) + 1
    record = {
        "id": event_id,
        "name": request.name,
        "code": request.code,
        "level": request.level,
        "category": request.category,
        "mark": request.mark,
        "icon_name": request.iconName,
        "source": request.source,
        "event_source": request.eventSource,
        "algorithm_code": request.algorithmCode,
        "attrs": [item.model_dump() for item in request.attrs],
        "sort_order": sort_order,
        "enabled": request.enabled,
        "created_at": now,
        "updated_at": now,
    }
    state.event_infos_store[event_id] = record
    persist_event_info(record)
    return event_info_out(record)


@router.put("/api/event-infos/{event_id}", response_model=EventInfoOut)
def update_event_info(event_id: str, request: EventInfoUpdate) -> EventInfoOut:
    """更新事件信息；缺省字段保留原值。「算法编码」变更时级联刷新引用该事件的布控任务。"""
    record = require_event_info(event_id)
    # 布控任务按事件编码引用事件信息，级联匹配要用修改前的编码
    old_code = str(record.get("code") or "")
    old_algorithm_code = str(record.get("algorithm_code") or "")
    if request.name is not None:
        record["name"] = request.name
    if request.code is not None:
        record["code"] = request.code
    if request.level is not None:
        record["level"] = request.level
    if request.category is not None:
        record["category"] = request.category
    if request.mark is not None:
        record["mark"] = request.mark
    if request.iconName is not None:
        record["icon_name"] = request.iconName
    if request.source is not None:
        record["source"] = request.source
    if request.eventSource is not None:
        record["event_source"] = request.eventSource
    if request.algorithmCode is not None:
        record["algorithm_code"] = request.algorithmCode
    if request.attrs is not None:
        record["attrs"] = [item.model_dump() for item in request.attrs]
    if request.sortOrder is not None:
        record["sort_order"] = request.sortOrder
    if request.enabled is not None:
        record["enabled"] = request.enabled
    record["updated_at"] = datetime.now(timezone.utc)
    persist_event_info(record)
    new_algorithm_code = str(record.get("algorithm_code") or "")
    if request.algorithmCode is not None and new_algorithm_code != old_algorithm_code:
        cascade_event_algorithm_to_tasks(old_code, new_algorithm_code)
    return event_info_out(record)


@router.delete("/api/event-infos/{event_id}")
def delete_event_info(event_id: str) -> dict[str, str]:
    """删除事件信息：被复核类型/复核任务引用时 409 拒绝，否则移出内存并删库。"""
    record = require_event_info(event_id)
    assert_event_info_not_referenced(record)
    state.event_infos_store.pop(event_id, None)
    delete_event_info_from_db(event_id)
    return {"deleted": event_id}
