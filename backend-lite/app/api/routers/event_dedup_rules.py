"""事件去重规则 CRUD 路由。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.event_dedup_rule import DedupRuleCreate, DedupRuleOut, DedupRuleUpdate
from app.services.event_dedup_rules import (
    dedup_rule_out,
    delete_dedup_rule_from_db,
    persist_dedup_rule,
    require_dedup_rule,
)

router = APIRouter()


@router.get("/api/event-dedup-rules", response_model=list[DedupRuleOut])
def list_dedup_rules() -> list[DedupRuleOut]:
    """按创建时间倒序返回全部去重规则。"""
    records = sorted(state.event_dedup_rules_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [dedup_rule_out(record) for record in records]


@router.post("/api/event-dedup-rules", response_model=DedupRuleOut)
def create_dedup_rule(request: DedupRuleCreate) -> DedupRuleOut:
    """创建去重规则：生成 uuid，入内存并落库。"""
    rule_id = str(uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "id": rule_id,
        "name": request.name,
        "algorithm": request.algorithm,
        "strategy": request.strategy,
        "duration_minutes": request.durationMinutes,
        "similarity": request.similarity,
        "all_cameras": request.allCameras,
        "cameras": request.cameras,
        "remark": request.remark,
        "enabled": request.enabled,
        "created_at": now,
        "updated_at": now,
    }
    state.event_dedup_rules_store[rule_id] = record
    persist_dedup_rule(record)
    return dedup_rule_out(record)


@router.put("/api/event-dedup-rules/{rule_id}", response_model=DedupRuleOut)
def update_dedup_rule(rule_id: str, request: DedupRuleUpdate) -> DedupRuleOut:
    """更新去重规则；缺省字段保留原值。"""
    record = require_dedup_rule(rule_id)
    if request.name is not None:
        record["name"] = request.name
    if request.algorithm is not None:
        record["algorithm"] = request.algorithm
    if request.strategy is not None:
        record["strategy"] = request.strategy
    if request.durationMinutes is not None:
        record["duration_minutes"] = request.durationMinutes
    if request.similarity is not None:
        record["similarity"] = request.similarity
    if request.allCameras is not None:
        record["all_cameras"] = request.allCameras
    if request.cameras is not None:
        record["cameras"] = request.cameras
    if request.remark is not None:
        record["remark"] = request.remark
    if request.enabled is not None:
        record["enabled"] = request.enabled
    record["updated_at"] = datetime.now(timezone.utc)
    persist_dedup_rule(record)
    return dedup_rule_out(record)


@router.delete("/api/event-dedup-rules/{rule_id}")
def delete_dedup_rule(rule_id: str) -> dict[str, str]:
    """删除去重规则：移出内存并删库。"""
    record = state.event_dedup_rules_store.pop(rule_id, None)
    if not record:
        raise HTTPException(status_code=404, detail="Dedup rule not found")
    delete_dedup_rule_from_db(rule_id)
    return {"deleted": rule_id}
