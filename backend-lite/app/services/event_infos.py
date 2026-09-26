"""事件信息的内存态与数据库持久化。"""

import logging
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal, engine
from app.models.event_info import EventInfoORM
from app.schemas.event_info import EventInfoOut
from app.services.deployment_tasks import persist_deployment_task
from app.services.worker_streams import sync_worker_streams_for_task

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


def assert_event_info_not_referenced(record: dict[str, Any]) -> None:
    """删除前校验事件信息未被复核类型或复核任务引用。

    复核类型按事件编码（code）引用事件信息；复核任务创建时快照了
    review_type_code，同样按编码判断。

    Args:
        record: 待删除的事件信息字典。

    Raises:
        HTTPException: 被引用时 409，detail 说明引用来源。
    """
    code = str(record["code"])
    used_by_types = [
        str(item["name"])
        for item in state.review_types_store.values()
        if str(item.get("code")) == code
    ]
    if used_by_types:
        raise HTTPException(
            status_code=409,
            detail=f"事件配置已被复核类型「{used_by_types[0]}」引用，无法删除",
        )
    used_by_tasks = any(
        str(item.get("review_type_code")) == code
        for item in state.review_tasks_store.values()
    )
    if used_by_tasks:
        raise HTTPException(
            status_code=409,
            detail="事件配置已被复核任务引用，无法删除",
        )


def cascade_event_algorithm_to_tasks(event_code: str, bound_algorithm_code: str) -> int:
    """事件信息「算法编码」变更后，级联更新引用该事件的布控任务的算法快照。

    布控任务的 algorithmCode 存的是事件编码（布控弹窗的「算法编号」），
    algorithmId/algorithmName/engineType/pipeline 是保存时的算法快照；事件配置里
    改了「算法编码」后快照即过期。这里按与前端 resolveEventAlgorithm 相同的口径
    重新解析：优先事件绑定的算法编码，绑定为空或未命中时回落到事件编码本身对应
    的算法；都匹配不到则解绑。同步落库并刷新 worker 流。

    Args:
        event_code: 事件编码（布控任务按 algorithmCode 引用它）。
        bound_algorithm_code: 事件信息修改后的算法编码。

    Returns:
        实际更新的布控任务数。
    """
    code = event_code.strip()
    if not code:
        return 0
    candidates = [item for item in (bound_algorithm_code.strip(), code) if item]
    algorithm = next(
        (
            algo
            for candidate in candidates
            for algo in state.algorithms_store.values()
            if algo.code.strip() == candidate
        ),
        None,
    )
    now = datetime.now(timezone.utc)
    updated_count = 0
    for task in list(state.deployment_tasks_store.values()):
        if (task.algorithmCode or "").strip() != code:
            continue
        updated = task.model_copy(
            update={
                "algorithmId": algorithm.id if algorithm else None,
                "algorithmName": algorithm.name if algorithm else None,
                "engineType": algorithm.engineType if algorithm else None,
                "pipeline": algorithm.name if algorithm else "",
                "updatedAt": now,
            }
        )
        state.deployment_tasks_store[task.id] = updated
        persist_deployment_task(updated)
        sync_worker_streams_for_task(task)
        sync_worker_streams_for_task(updated)
        updated_count += 1
    return updated_count


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
