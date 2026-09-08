"""布控事件存储表（deployment_events）的查询服务。"""

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.deployment_event import DeploymentEventORM
from app.schemas.event import (
    DeploymentEventAreaItem,
    DeploymentEventItem,
    DeploymentEventReviewItem,
    DeploymentEventStats,
    DeploymentEventSummary,
    DeploymentEventTrendItem,
    ObjectInfo,
)
from app.services.events import EVENT_TYPE_FACE_MATCH, EVENT_TYPE_OBJECT_DETECTION, _task_algorithm_code

logger = logging.getLogger(__name__)

REVIEW_STATUS_VALID = "有效"
REVIEW_STATUS_INVALID = "无效"
AREA_FALLBACK = "未分区"
STATS_AREA_TOP_N = 5


def update_deployment_event_review_status(event_id: str, verdict: str) -> None:
    """回写布控事件复核状态（大模型判定结论）；失败仅记录日志。

    Args:
        event_id: deployment_events.id（UUID 字符串）。
        verdict: 复核结论（有效/无效）。
    """
    try:
        with SessionLocal() as pgdb:
            pgdb.query(DeploymentEventORM).filter(DeploymentEventORM.id == UUID(event_id)).update(
                {"review_status": verdict}
            )
            pgdb.commit()
    except (SQLAlchemyError, ValueError) as exc:
        logger.error("deployment event review status update failed: %s", exc)


def deployment_event_item(row: DeploymentEventORM) -> DeploymentEventItem:
    """ORM 行转对外 camelCase 条目。"""
    return DeploymentEventItem(
        id=row.id,
        deploymentTaskId=row.deployment_task_id,
        eventType=row.event_type,
        algorithmCode=row.algorithm_code or _task_algorithm_code(row.deployment_task_id),
        reviewStatus=row.review_status,
        faceProfileId=row.face_profile_id,
        faceProfileName=row.face_profile_name,
        faceProfilePhotoUrl=row.face_profile_photo_url,
        objects=[ObjectInfo(**obj) for obj in row.objects] if row.objects else None,
        frameWidth=row.frame_width or 0,
        frameHeight=row.frame_height or 0,
        snapshotUrl=row.snapshot_url,
        cameraId=row.camera_id,
        cameraName=row.camera_name,
        cameraArea=row.camera_area,
        similarity=float(row.similarity) if row.similarity is not None else None,
        occurredAt=row.occurred_at,
        createdAt=row.created_at,
    )


def query_deployment_events(
    *,
    page: int,
    size: int,
    task_id: UUID | None = None,
    camera_id: UUID | None = None,
    event_type: str | None = None,
    keyword: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[DeploymentEventItem], int]:
    """按条件分页查询布控事件，返回 (items, total)，按发生时间倒序。"""
    with SessionLocal() as pgdb:
        query = pgdb.query(DeploymentEventORM)
        if task_id is not None:
            query = query.filter(DeploymentEventORM.deployment_task_id == task_id)
        if camera_id is not None:
            query = query.filter(DeploymentEventORM.camera_id == camera_id)
        if event_type:
            if event_type == EVENT_TYPE_OBJECT_DETECTION:
                # 目标检测为聚合桶：worker 上报的算法 eventType 各异，统一匹配非人脸事件
                query = query.filter(DeploymentEventORM.event_type != EVENT_TYPE_FACE_MATCH)
            else:
                query = query.filter(DeploymentEventORM.event_type == event_type)
        if keyword:
            like = f"%{keyword.strip()}%"
            query = query.filter(
                or_(
                    DeploymentEventORM.face_profile_name.ilike(like),
                    DeploymentEventORM.camera_name.ilike(like),
                )
            )
        if start_time is not None:
            query = query.filter(DeploymentEventORM.occurred_at >= start_time)
        if end_time is not None:
            query = query.filter(DeploymentEventORM.occurred_at <= end_time)
        total = query.count()
        rows = (
            query.order_by(DeploymentEventORM.occurred_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return [deployment_event_item(row) for row in rows], total


def deployment_events_summary() -> DeploymentEventSummary:
    """布控事件统计：总数 / 今日新增 / 人脸比对 / 目标检测。"""
    with SessionLocal() as pgdb:
        total = pgdb.query(func.count(DeploymentEventORM.id)).scalar() or 0
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today = (
            pgdb.query(func.count(DeploymentEventORM.id))
            .filter(DeploymentEventORM.occurred_at >= today_start)
            .scalar()
            or 0
        )
        face_match = (
            pgdb.query(func.count(DeploymentEventORM.id))
            .filter(DeploymentEventORM.event_type == EVENT_TYPE_FACE_MATCH)
            .scalar()
            or 0
        )
        return DeploymentEventSummary(
            total=total,
            today=today,
            faceMatch=face_match,
            objectDetection=total - face_match,
        )


def _fill_daily_trend(
    rows: list[tuple[object, int]],
    start_date: date,
    end_date: date,
) -> list[DeploymentEventTrendItem]:
    """把 (日期, 计数) 聚合行补齐为连续逐日趋势（无事件的日期计 0）。

    Args:
        rows: func.date 分组结果，日期元素为 date 或 ISO 字符串。
        start_date: 起始日期（含）。
        end_date: 结束日期（含）。

    Returns:
        按日期升序的逐日计数，YYYY-MM-DD 字符串键。
    """
    counts: dict[str, int] = {}
    for day, count in rows:
        key = day.isoformat() if isinstance(day, date) else str(day)
        counts[key] = int(count)
    trend: list[DeploymentEventTrendItem] = []
    current = start_date
    while current <= end_date:
        trend.append(DeploymentEventTrendItem(date=current.isoformat(), count=counts.get(current.isoformat(), 0)))
        current += timedelta(days=1)
    return trend


def deployment_events_stats(
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    area: str | None = None,
) -> DeploymentEventStats:
    """事件统计页聚合：趋势 / 类型分布 / 区域排行 / 复核统计。

    时间范围缺省为近 7 天（含今天）；today/week 卡片只应用区域过滤。
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    range_end = end_time or now
    range_start = start_time or (today_start - timedelta(days=6))
    with SessionLocal() as pgdb:
        base = pgdb.query(DeploymentEventORM).filter(
            DeploymentEventORM.occurred_at >= range_start,
            DeploymentEventORM.occurred_at <= range_end,
        )
        if area:
            base = base.filter(DeploymentEventORM.camera_area == area)

        # 按 (event_type, review_status) 分组一次聚合，派生总数/类型/复核口径
        grouped = (
            base.with_entities(
                DeploymentEventORM.event_type,
                DeploymentEventORM.review_status,
                func.count(),
            )
            .group_by(DeploymentEventORM.event_type, DeploymentEventORM.review_status)
            .all()
        )
        total = 0
        face_match = 0
        valid = 0
        invalid = 0
        unreviewed = 0
        face_review = {"valid": 0, "invalid": 0, "unreviewed": 0}
        object_review = {"valid": 0, "invalid": 0, "unreviewed": 0}
        for event_type, review_status, count in grouped:
            count = int(count)
            total += count
            bucket = face_review if event_type == EVENT_TYPE_FACE_MATCH else object_review
            if event_type == EVENT_TYPE_FACE_MATCH:
                face_match += count
            if review_status == REVIEW_STATUS_VALID:
                valid += count
                bucket["valid"] += count
            elif review_status == REVIEW_STATUS_INVALID:
                invalid += count
                bucket["invalid"] += count
            else:
                unreviewed += count
                bucket["unreviewed"] += count

        trend_rows = (
            base.with_entities(func.date(DeploymentEventORM.occurred_at), func.count())
            .group_by(func.date(DeploymentEventORM.occurred_at))
            .all()
        )
        trend = _fill_daily_trend(trend_rows, range_start.date(), range_end.date())

        area_rows = (
            base.with_entities(DeploymentEventORM.camera_area, func.count())
            .group_by(DeploymentEventORM.camera_area)
            .order_by(func.count().desc())
            .all()
        )
        by_area = [
            DeploymentEventAreaItem(area=name or AREA_FALLBACK, count=int(count))
            for name, count in area_rows[:STATS_AREA_TOP_N]
        ]

        area_filter = pgdb.query(DeploymentEventORM).filter(
            DeploymentEventORM.occurred_at >= range_start,
            DeploymentEventORM.occurred_at <= range_end,
        )
        areas = [
            str(name)
            for (name,) in area_filter.with_entities(DeploymentEventORM.camera_area)
            .filter(
                DeploymentEventORM.camera_area.isnot(None),
                DeploymentEventORM.camera_area != "",
            )
            .distinct()
            .order_by(DeploymentEventORM.camera_area)
            .all()
        ]

        # today/week 卡片：只应用区域过滤，不受所选时间范围影响
        scoped = pgdb.query(DeploymentEventORM)
        if area:
            scoped = scoped.filter(DeploymentEventORM.camera_area == area)
        today = scoped.filter(DeploymentEventORM.occurred_at >= today_start).count()
        week = scoped.filter(DeploymentEventORM.occurred_at >= today_start - timedelta(days=6)).count()

        reviewed = valid + invalid
        return DeploymentEventStats(
            total=total,
            today=today,
            week=week,
            unreviewed=unreviewed,
            reviewRate=reviewed / total if total else 0.0,
            faceMatch=face_match,
            objectDetection=total - face_match,
            areas=areas,
            trend=trend,
            byArea=by_area,
            reviewByType=[
                DeploymentEventReviewItem(eventType=EVENT_TYPE_FACE_MATCH, **face_review),
                DeploymentEventReviewItem(eventType=EVENT_TYPE_OBJECT_DETECTION, **object_review),
            ],
        )
