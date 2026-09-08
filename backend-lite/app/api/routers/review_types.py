"""复核类型 CRUD 路由。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.review_type import ReviewTypeCreate, ReviewTypeOut, ReviewTypeUpdate
from app.services.review_types import (
    delete_review_type_from_db,
    persist_review_type,
    require_review_type,
    review_type_out,
)

router = APIRouter()


@router.get("/api/review-types", response_model=list[ReviewTypeOut])
def list_review_types() -> list[ReviewTypeOut]:
    """按创建时间倒序返回全部复核类型。"""
    records = sorted(state.review_types_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [review_type_out(record) for record in records]


@router.post("/api/review-types", response_model=ReviewTypeOut)
def create_review_type(request: ReviewTypeCreate) -> ReviewTypeOut:
    """创建复核类型：生成 uuid，入内存并落库。"""
    type_id = str(uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "id": type_id,
        "name": request.name,
        "code": request.code,
        "prompt": request.prompt,
        "inject_event": request.injectEvent or "",
        "remark": request.remark or "",
        "llm_config_id": request.llmConfigId or None,
        "created_at": now,
        "updated_at": now,
    }
    state.review_types_store[type_id] = record
    persist_review_type(record)
    return review_type_out(record)


@router.put("/api/review-types/{type_id}", response_model=ReviewTypeOut)
def update_review_type(type_id: str, request: ReviewTypeUpdate) -> ReviewTypeOut:
    """更新复核类型；仅更新非 None 字段。"""
    record = require_review_type(type_id)
    if request.name is not None:
        record["name"] = request.name
    if request.code is not None:
        record["code"] = request.code
    if request.prompt is not None:
        record["prompt"] = request.prompt
    if request.injectEvent is not None:
        record["inject_event"] = request.injectEvent
    if request.remark is not None:
        record["remark"] = request.remark
    if request.llmConfigId is not None:  # 空字符串表示清除关联
        record["llm_config_id"] = request.llmConfigId or None
    record["updated_at"] = datetime.now(timezone.utc)
    persist_review_type(record)
    return review_type_out(record)


@router.delete("/api/review-types/{type_id}")
def delete_review_type(type_id: str) -> dict[str, str]:
    """删除复核类型：移出内存并删库。"""
    record = state.review_types_store.pop(type_id, None)
    if not record:
        raise HTTPException(status_code=404, detail="Review type not found")
    delete_review_type_from_db(type_id)
    return {"deleted": type_id}
