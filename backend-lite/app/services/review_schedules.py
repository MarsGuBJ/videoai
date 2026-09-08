"""定时复核任务的内存态、数据库持久化、cron 调度与批量执行。

执行流程：按 batch_size 抽取未复核布控事件 → 逐条读快照、建复核任务、
调大模型判定 → verdict 非空时回写事件 review_status → 汇总写入 last_result。
判定失败不回写 review_status（下次触发重试，计入失败数）。
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from croniter import croniter
from fastapi import HTTPException
from sqlalchemy import Table, or_
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models.deployment_event import DeploymentEventORM
from app.models.review_schedule import ReviewScheduleORM
from app.schemas.review_schedule import ReviewScheduleOut
from app.services import llm_client
from app.services.deployment_events import REVIEW_STATUS_VALID, update_deployment_event_review_status
from app.services.review_tasks import persist_review_task
from app.utils.assets import asset_path

logger = logging.getLogger(__name__)

SCHEDULER_TICK_SECONDS = 30
MAX_ERROR_REASON_CHARS = 500

# 正在执行中的 schedule id 集合（防同一定时任务并发重入）
_running_schedule_ids: set[str] = set()
_running_schedule_ids_lock = threading.Lock()


def require_review_schedule(schedule_id: str) -> dict[str, Any]:
    """按 ID 取定时复核任务，不存在则 404。

    Args:
        schedule_id: 定时复核任务 ID。

    Returns:
        内存态中的定时复核任务字典。

    Raises:
        HTTPException: 定时复核任务不存在时 404。
    """
    record = state.review_schedules_store.get(schedule_id)
    if not record:
        raise HTTPException(status_code=404, detail="Review schedule not found")
    return record


def review_schedule_out(record: dict[str, Any]) -> ReviewScheduleOut:
    """把内存态定时复核任务字典转为对外 DTO。

    Args:
        record: 内存态定时复核任务字典。

    Returns:
        camelCase 对外 DTO。
    """
    return ReviewScheduleOut(
        id=str(record["id"]),
        name=str(record["name"]),
        cron=str(record["cron"]),
        enabled=bool(record["enabled"]),
        batchSize=int(record["batch_size"]),
        reviewTypeId=str(record["review_type_id"]),
        reviewTypeName=str(record["review_type_name"]),
        reviewTypeCode=str(record["review_type_code"]),
        lastRunAt=record.get("last_run_at"),
        lastResult=str(record.get("last_result") or ""),
        createdAt=record["created_at"],
        updatedAt=record["updated_at"],
    )


def ensure_review_schedule_schema() -> None:
    """轻量迁移：确保 review_schedules 表存在（幂等，容错不阻断启动）。"""
    try:
        with engine.begin() as conn:
            cast(Table, ReviewScheduleORM.__table__).create(conn, checkfirst=True)
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("review schedule schema ensure failed: %s", exc)


def load_review_schedules_from_db() -> None:
    """启动时把数据库中的定时复核任务载入内存存储。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(ReviewScheduleORM).all()
            state.review_schedules_store.clear()
            for row in rows:
                state.review_schedules_store[str(row.id)] = {
                    "id": str(row.id),
                    "name": row.name,
                    "cron": row.cron,
                    "enabled": row.enabled,
                    "batch_size": row.batch_size,
                    "review_type_id": row.review_type_id,
                    "review_type_name": row.review_type_name,
                    "review_type_code": row.review_type_code,
                    "last_run_at": row.last_run_at,
                    "last_result": row.last_result or "",
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
    except SQLAlchemyError as exc:  # 数据库不可达时以空调度集启动（与复核类型一致）
        logger.error("review schedule load failed: %s", exc)


def persist_review_schedule(record: dict[str, Any]) -> None:
    """把定时复核任务 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的定时复核任务字典。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(ReviewScheduleORM, str(record["id"]))
            if row is None:
                row = ReviewScheduleORM(id=str(record["id"]))
                pgdb.add(row)
            row.name = str(record["name"])
            row.cron = str(record["cron"])
            row.enabled = bool(record["enabled"])
            row.batch_size = int(record["batch_size"])
            row.review_type_id = str(record["review_type_id"])
            row.review_type_name = str(record["review_type_name"])
            row.review_type_code = str(record["review_type_code"])
            row.last_run_at = record.get("last_run_at")
            row.last_result = str(record.get("last_result") or "")
            row.created_at = record["created_at"]
            row.updated_at = record["updated_at"]
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("review schedule persist failed: %s", exc)


def delete_review_schedule_from_db(schedule_id: str) -> None:
    """从数据库删除定时复核任务；失败仅记录日志。

    Args:
        schedule_id: 定时复核任务 ID。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(ReviewScheduleORM, schedule_id)
            if row is not None:
                pgdb.delete(row)
                pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("review schedule delete failed: %s", exc)


def validate_cron(expr: str) -> None:
    """校验 cron 表达式合法性。

    Args:
        expr: cron 表达式（5 段）。

    Raises:
        ValueError: 表达式非法。
    """
    if not croniter.is_valid(expr):
        raise ValueError(f"invalid cron expression: {expr}")


def _read_snapshot_bytes(snapshot_url: str) -> bytes | None:
    """按快照 URL 读取本地快照字节；路径非法或文件不存在返回 None。

    Args:
        snapshot_url: ``/api/assets/snapshots/<file>`` 形式的 URL。

    Returns:
        图片字节；读不到时返回 None。
    """
    path = asset_path(snapshot_url, get_settings().snapshot_storage_dir)
    if path is None or not path.is_file():
        return None
    try:
        return path.read_bytes()
    except OSError as exc:
        logger.error("snapshot read failed: %s", exc)
        return None


def _query_pending_events(schedule: dict[str, Any]) -> list[tuple[str, str]]:
    """抽取待复核事件：匹配 algorithm_code、复核状态为空、带快照，按发生时间升序限量。

    Args:
        schedule: 内存态定时复核任务字典。

    Returns:
        (事件 ID, 快照 URL) 列表，最多 batch_size 条。
    """
    batch_size = int(schedule.get("batch_size") or 50)
    with SessionLocal() as pgdb:
        rows = (
            pgdb.query(DeploymentEventORM.id, DeploymentEventORM.snapshot_url)
            .filter(
                DeploymentEventORM.algorithm_code == str(schedule["review_type_code"]),
                or_(DeploymentEventORM.review_status.is_(None), DeploymentEventORM.review_status == ""),
                DeploymentEventORM.snapshot_url.isnot(None),
                DeploymentEventORM.snapshot_url != "",
            )
            .order_by(DeploymentEventORM.occurred_at.asc())
            .limit(batch_size)
            .all()
        )
        return [(str(event_id), str(snapshot_url)) for event_id, snapshot_url in rows]


def _review_single_event(schedule: dict[str, Any], event_id: str, snapshot_url: str) -> str:
    """对单条事件执行复核：读快照 → 建复核任务 → 大模型判定 → 回写事件复核状态。

    Args:
        schedule: 内存态定时复核任务字典。
        event_id: 布控事件 ID。
        snapshot_url: 事件快照 URL。

    Returns:
        结果分类："valid" / "invalid" / "failed" / "skipped"。
    """
    image_bytes = _read_snapshot_bytes(snapshot_url)
    if image_bytes is None:
        return "skipped"
    review_type = state.review_types_store.get(str(schedule["review_type_id"]))
    llm_config_id = str(review_type.get("llm_config_id") or "") if review_type else ""
    llm_cfg = state.llm_configs_store.get(llm_config_id) if llm_config_id else None
    now = datetime.now(timezone.utc)
    task_id = str(uuid4())
    record = {
        "id": task_id,
        "review_type_id": str(schedule["review_type_id"]),
        "review_type_name": str(schedule["review_type_name"]),
        "review_type_code": str(schedule["review_type_code"]),
        "llm_config_id": llm_config_id,
        "llm_config_name": str(llm_cfg["name"]) if llm_cfg else "",
        "image_url": snapshot_url,
        "status": "进行中",
        "verdict": "",
        "reason": "",
        "created_at": now,
        "updated_at": now,
    }
    state.review_tasks_store[task_id] = record
    persist_review_task(record)
    if review_type is None or llm_cfg is None:
        record["status"] = "失败"
        record["reason"] = "无大模型配置"
        record["updated_at"] = datetime.now(timezone.utc)
        persist_review_task(record)
        return "failed"
    try:
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
    except Exception as exc:  # noqa: BLE001  # 单条事件判定失败仅计入失败数，不中断整批
        logger.error("review schedule event judgment failed (%s): %s", event_id, exc)
        record["status"] = "失败"
        record["reason"] = str(exc)[:MAX_ERROR_REASON_CHARS]
    record["updated_at"] = datetime.now(timezone.utc)
    persist_review_task(record)
    if record["status"] != "已完成":
        return "failed"
    verdict = str(record["verdict"])
    if not verdict:  # 模型输出解析失败：不回写 review_status，下次触发重试
        return "failed"
    update_deployment_event_review_status(event_id, verdict)
    return "valid" if verdict == REVIEW_STATUS_VALID else "invalid"


def execute_review_schedule(schedule_id: str) -> None:
    """执行一次定时复核：批量抽取未复核事件逐条判定，汇总写入 last_result（永不抛异常）。

    Args:
        schedule_id: 定时复核任务 ID。
    """
    try:
        schedule = state.review_schedules_store.get(schedule_id)
        if not schedule:
            logger.error("review schedule execution skipped, schedule not found: %s", schedule_id)
            return
        events = _query_pending_events(schedule)
        counts = {"valid": 0, "invalid": 0, "failed": 0, "skipped": 0}
        for event_id, snapshot_url in events:
            outcome = _review_single_event(schedule, event_id, snapshot_url)
            counts[outcome] += 1
        schedule["last_result"] = (
            f"处理 {len(events)} 条：有效 {counts['valid']} / 无效 {counts['invalid']}"
            f" / 失败 {counts['failed']} / 跳过 {counts['skipped']}"
        )
        now = datetime.now(timezone.utc)
        schedule["last_run_at"] = now
        schedule["updated_at"] = now
        persist_review_schedule(schedule)
    except Exception as exc:  # noqa: BLE001  # 调度线程内任何失败都仅记录日志，不影响后续调度
        logger.error("review schedule execution failed: %s", exc)


def _schedule_due(schedule: dict[str, Any]) -> bool:
    """判断定时任务是否到点：cron 相对上次运行（或创建时间）的下一触发时刻已过。

    Args:
        schedule: 内存态定时复核任务字典。

    Returns:
        到点返回 True。

    Raises:
        ValueError: cron 表达式非法。
    """
    now = datetime.now(timezone.utc)
    base = schedule.get("last_run_at") or schedule["created_at"]
    if base.tzinfo is None:  # 统一按 UTC 处理，避免 naive/aware 混用
        base = base.replace(tzinfo=timezone.utc)
    next_run = croniter(str(schedule["cron"]), base).get_next(datetime)
    return next_run <= now


def trigger_review_schedule(schedule_id: str) -> bool:
    """起独立 daemon 线程执行定时复核；同一任务执行中不重入。

    Args:
        schedule_id: 定时复核任务 ID。

    Returns:
        成功启动返回 True；已在执行中返回 False。
    """
    with _running_schedule_ids_lock:
        if schedule_id in _running_schedule_ids:
            return False
        _running_schedule_ids.add(schedule_id)
    threading.Thread(target=_execute_and_release, args=(schedule_id,), daemon=True).start()
    return True


def _execute_and_release(schedule_id: str) -> None:
    """执行定时任务并释放重入锁。

    Args:
        schedule_id: 定时复核任务 ID。
    """
    try:
        execute_review_schedule(schedule_id)
    finally:
        with _running_schedule_ids_lock:
            _running_schedule_ids.discard(schedule_id)


def review_schedule_loop(stop_event: threading.Event) -> None:
    """调度循环：每 30 秒检查一次各定时任务是否到点，到点起独立线程执行。

    Args:
        stop_event: 停止信号（来自 lifespan shutdown）。
    """
    while not stop_event.wait(SCHEDULER_TICK_SECONDS):
        for schedule_id, schedule in list(state.review_schedules_store.items()):
            if not schedule.get("enabled"):
                continue
            try:
                if not _schedule_due(schedule):
                    continue
            except Exception as exc:  # noqa: BLE001  # cron 解析异常跳过，不影响其他任务
                logger.error("review schedule cron parse failed (%s): %s", schedule_id, exc)
                continue
            trigger_review_schedule(schedule_id)
