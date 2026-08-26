"""事件查询、摄取与 SSE 推送路由。"""

import logging
import queue
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.db.session import SessionLocal
from app.models.face_match_event import FaceMatchEventORM
from app.schemas.event import (
    FaceEventIngestRequest,
    FaceEventResponse,
    FaceMatchEventResponse,
    ObjectEventIngestRequest,
    ObjectEventResponse,
)
from app.schemas.face import FaceScanSummary
from app.services.events import (
    EVENT_SUBSCRIBER_QUEUE_SIZE,
    EVENTS_STORE_MAX_SIZE,
    FaceEventInput,
    broadcast_event,
    create_face_event,
)
from app.services.face_scan import scan_running_cameras
from app.services.faces import require_face
from app.utils.assets import save_snapshot

logger = logging.getLogger(__name__)

EVENTS_DEFAULT_LIMIT = 100
EVENTS_MAX_LIMIT = 200
EVENTS_MATCH_DEFAULT_LIMIT = 10
EVENTS_MATCH_MAX_LIMIT = 10
FACE_MATCH_EVENTS_DEFAULT_LIMIT = 100
FACE_MATCH_EVENTS_MAX_LIMIT = 500
OBJECT_EVENTS_DEFAULT_LIMIT = 100
OBJECT_EVENTS_MAX_LIMIT = 200
OBJECT_EVENT_COOLDOWN_SECONDS = 2.0
EVENT_STREAM_KEEPALIVE_SECONDS = 15

router = APIRouter()


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


@router.get("/api/face-match-events", response_model=list[FaceMatchEventResponse])
def list_face_match_events(limit: int = FACE_MATCH_EVENTS_DEFAULT_LIMIT) -> list[FaceMatchEventResponse]:
    """从数据库查询人脸匹配事件；数据库不可达时返回空列表（与原逻辑一致）。"""
    safe_limit = max(1, min(limit, FACE_MATCH_EVENTS_MAX_LIMIT))
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(FaceMatchEventORM).order_by(FaceMatchEventORM.matched_at.desc()).limit(safe_limit).all()
            return [
                FaceMatchEventResponse(
                    id=row.id,
                    deploymentTaskId=row.deployment_task_id,
                    faceProfileId=row.face_profile_id,
                    faceProfileName=row.face_profile_name,
                    faceProfilePhotoUrl=row.face_profile_photo_url,
                    snapshotUrl=row.snapshot_url,
                    cameraId=row.camera_id,
                    cameraName=row.camera_name,
                    cameraArea=row.camera_area,
                    similarity=float(row.similarity or 0.0),
                    matchedAt=row.matched_at,
                    createdAt=row.created_at,
                )
                for row in rows
            ]
    except SQLAlchemyError as exc:
        logger.error("face-match-events query failed: %s", exc)
        return []


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
    camera_key = str(request.cameraId)
    now_ts = time.time()
    cooldown_key = f"{camera_key}:objects"
    with state.event_lock:
        last_time = state.object_event_cooldowns.get(cooldown_key, 0)
        if now_ts - last_time < OBJECT_EVENT_COOLDOWN_SECONDS:
            return None
        state.object_event_cooldowns[cooldown_key] = now_ts

    now = datetime.now(timezone.utc)
    event = ObjectEventResponse(
        id=uuid4(),
        cameraId=request.cameraId,
        cameraName=request.cameraName,
        objects=request.objects,
        snapshotUrl=save_snapshot(request.snapshotBase64),
        videoTime=request.videoTime,
        frameWidth=request.frameWidth,
        frameHeight=request.frameHeight,
        createdAt=now,
    )
    payload = f"event: object-event\ndata: {event.model_dump_json()}\n\n"
    with state.event_lock:
        state.object_events_store.insert(0, event)
        del state.object_events_store[EVENTS_STORE_MAX_SIZE:]
    broadcast_event(payload)
    return event


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
