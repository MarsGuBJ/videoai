"""事件查询、摄取与 SSE 推送路由。"""

import logging
import queue
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.schemas.event import (
    DeploymentEventPage,
    DeploymentEventStats,
    DeploymentEventSummary,
    FaceEventIngestRequest,
    FaceEventResponse,
    ObjectEventIngestRequest,
    ObjectEventResponse,
)
from app.schemas.face import FaceScanSummary
from app.services.deployment_events import (
    deployment_events_stats,
    deployment_events_summary,
    query_deployment_events,
)
from app.services.events import (
    EVENT_SUBSCRIBER_QUEUE_SIZE,
    FaceEventInput,
    ObjectEventInput,
    create_face_event,
    create_object_event,
)
from app.services.face_scan import scan_running_cameras
from app.services.faces import require_face

logger = logging.getLogger(__name__)

EVENTS_DEFAULT_LIMIT = 100
EVENTS_MAX_LIMIT = 200
EVENTS_MATCH_DEFAULT_LIMIT = 10
EVENTS_MATCH_MAX_LIMIT = 10
OBJECT_EVENTS_DEFAULT_LIMIT = 100
OBJECT_EVENTS_MAX_LIMIT = 200
EVENT_STREAM_KEEPALIVE_SECONDS = 15
DEPLOYMENT_EVENTS_DEFAULT_PAGE_SIZE = 20
DEPLOYMENT_EVENTS_MAX_PAGE_SIZE = 100

router = APIRouter()


@router.get("/api/deployment-events", response_model=DeploymentEventPage)
def list_deployment_events(
    page: int = 1,
    size: int = DEPLOYMENT_EVENTS_DEFAULT_PAGE_SIZE,
    taskId: UUID | None = None,
    cameraId: UUID | None = None,
    eventType: str | None = None,
    keyword: str | None = None,
    startTime: datetime | None = None,
    endTime: datetime | None = None,
) -> DeploymentEventPage:
    """分页查询布控事件存储表；数据库不可达时返回空页。"""
    safe_page = max(1, page)
    safe_size = max(1, min(size, DEPLOYMENT_EVENTS_MAX_PAGE_SIZE))
    try:
        items, total = query_deployment_events(
            page=safe_page,
            size=safe_size,
            task_id=taskId,
            camera_id=cameraId,
            event_type=eventType,
            keyword=keyword,
            start_time=startTime,
            end_time=endTime,
        )
        return DeploymentEventPage(items=items, total=total, page=safe_page, size=safe_size)
    except SQLAlchemyError as exc:
        logger.error("deployment-events query failed: %s", exc)
        return DeploymentEventPage(items=[], total=0, page=safe_page, size=safe_size)


@router.get("/api/deployment-events/summary", response_model=DeploymentEventSummary)
def get_deployment_events_summary() -> DeploymentEventSummary:
    """布控事件统计：总数 / 今日新增 / 人脸比对 / 目标检测。"""
    try:
        return deployment_events_summary()
    except SQLAlchemyError as exc:
        logger.error("deployment-events summary failed: %s", exc)
        return DeploymentEventSummary(total=0, today=0, faceMatch=0, objectDetection=0)


@router.get("/api/deployment-events/stats", response_model=DeploymentEventStats)
def get_deployment_events_stats(
    startTime: datetime | None = None,
    endTime: datetime | None = None,
    area: str | None = None,
) -> DeploymentEventStats:
    """事件统计页聚合：趋势 / 类型分布 / 区域排行 / 复核统计；数据库不可达时返回全零。"""
    try:
        return deployment_events_stats(start_time=startTime, end_time=endTime, area=area)
    except SQLAlchemyError as exc:
        logger.error("deployment-events stats failed: %s", exc)
        return DeploymentEventStats(
            total=0,
            today=0,
            week=0,
            unreviewed=0,
            reviewRate=0.0,
            faceMatch=0,
            objectDetection=0,
            areas=[],
            trend=[],
            byArea=[],
            reviewByType=[],
        )


@router.get("/api/events", response_model=list[FaceEventResponse])
def events(limit: int = EVENTS_DEFAULT_LIMIT) -> list[FaceEventResponse]:
    """返回最近的人脸事件（新到旧）。"""
    safe_limit = max(1, min(limit, EVENTS_MAX_LIMIT))
    with state.event_lock:
        return state.events_store[:safe_limit]


@router.get("/api/events/match", response_model=list[FaceEventResponse])
def events_match(faceId: str = "", limit: int = EVENTS_MATCH_DEFAULT_LIMIT) -> list[FaceEventResponse]:
    """按人脸档案过滤事件，按视频时间倒序。"""
    safe_limit = max(1, min(limit, EVENTS_MATCH_MAX_LIMIT))
    with state.event_lock:
        if faceId:
            filtered = [e for e in state.events_store if str(e.faceProfileId) == faceId]
        else:
            filtered = list(state.events_store)
        filtered.sort(key=lambda e: e.videoTime, reverse=True)
        return filtered[:safe_limit]


@router.get("/api/events/stream")
def event_stream() -> StreamingResponse:
    """SSE 事件流：ready 事件 + 订阅队列推送 + keepalive。"""
    subscriber: queue.Queue[str] = queue.Queue(maxsize=EVENT_SUBSCRIBER_QUEUE_SIZE)
    with state.event_lock:
        state.event_subscribers.append(subscriber)

    def generator() -> Iterator[str]:
        yield "event: ready\ndata: ok\n\n"
        try:
            while True:
                try:
                    yield subscriber.get(timeout=EVENT_STREAM_KEEPALIVE_SECONDS)
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with state.event_lock:
                if subscriber in state.event_subscribers:
                    state.event_subscribers.remove(subscriber)

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.post("/api/events/ingest", response_model=FaceEventResponse | None)
def ingest_event(request: FaceEventIngestRequest) -> FaceEventResponse | None:
    """摄取外部上报的人脸事件（去重后入库并广播）。"""
    return create_face_event(
        FaceEventInput(
            camera_id=request.cameraId,
            face_profile_id=request.faceProfileId,
            camera_name=request.cameraName,
            profile_name=request.profileName,
            profile_description=request.profileDescription,
            face_photo_url=request.facePhotoPath or require_face(request.faceProfileId).photoUrl,
            snapshot_base64=request.snapshotBase64,
            video_time=request.videoTime,
            similarity=request.similarity,
            deployment_task_id=request.deploymentTaskId,
        )
    )


@router.post("/api/events/object-ingest", response_model=ObjectEventResponse | None)
def ingest_object_event(request: ObjectEventIngestRequest) -> ObjectEventResponse | None:
    """摄取目标检测事件；同摄像头 2 秒冷却期内直接丢弃。"""
    return create_object_event(
        ObjectEventInput(
            camera_id=request.cameraId,
            camera_name=request.cameraName,
            objects=request.objects,
            snapshot_base64=request.snapshotBase64,
            video_time=request.videoTime,
            frame_width=request.frameWidth,
            frame_height=request.frameHeight,
            event_type=request.eventType,
            deployment_task_id=request.deploymentTaskId,
        )
    )


@router.get("/api/events/objects", response_model=list[ObjectEventResponse])
def object_events(limit: int = OBJECT_EVENTS_DEFAULT_LIMIT) -> list[ObjectEventResponse]:
    """返回最近的目标检测事件（新到旧）。"""
    safe_limit = max(1, min(limit, OBJECT_EVENTS_MAX_LIMIT))
    with state.event_lock:
        return state.object_events_store[:safe_limit]


@router.post("/api/events/scan", response_model=FaceScanSummary)
def scan_events_now() -> FaceScanSummary:
    """立即触发一轮人脸扫描并返回摘要。"""
    return scan_running_cameras()
