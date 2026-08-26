"""事件总线：人脸/目标事件的创建、去重、入库与 SSE 广播。"""

import logging
import queue
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.face_match_event import FaceMatchEventORM
from app.schemas.event import FaceEventResponse
from app.services import camera_cache
from app.utils.assets import save_snapshot

logger = logging.getLogger(__name__)

EVENTS_STORE_MAX_SIZE = 200
EVENT_SUBSCRIBER_QUEUE_SIZE = 100


class FaceEventInput(BaseModel):
    """create_face_event 的入参封装（原函数参数超过 5 个，按规范收敛为模型）。"""

    camera_id: UUID
    face_profile_id: UUID
    camera_name: str
    profile_name: str
    profile_description: str | None = None
    face_photo_url: str
    snapshot_base64: str | None = None
    video_time: datetime
    similarity: float
    deployment_task_id: UUID | None = None


def broadcast_event(payload: str) -> None:
    """向全部 SSE 订阅者广播事件，剔除队列已满的失效订阅者。

    Args:
        payload: SSE 格式的完整事件文本。
    """
    with state.event_lock:
        stale: list[queue.Queue[str]] = []
        for subscriber in state.event_subscribers:
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                stale.append(subscriber)
        for subscriber in stale:
            if subscriber in state.event_subscribers:
                state.event_subscribers.remove(subscriber)


def create_face_event(event_input: FaceEventInput) -> FaceEventResponse | None:
    """创建人脸事件：去重、存快照、入内存队列、广播 SSE、落库。

    Args:
        event_input: 事件入参封装。

    Returns:
        新建的事件；命中冷却去重时返回 None。
    """
    if recent_duplicate_event(event_input.camera_id, event_input.face_profile_id, event_input.deployment_task_id):
        return None
    now = datetime.now(timezone.utc)
    snapshot_url = save_snapshot(event_input.snapshot_base64)
    event = FaceEventResponse(
        id=uuid4(),
        cameraId=event_input.camera_id,
        faceProfileId=event_input.face_profile_id,
        cameraName=event_input.camera_name,
        profileName=event_input.profile_name,
        profileDescription=event_input.profile_description,
        facePhotoUrl=event_input.face_photo_url,
        snapshotUrl=snapshot_url,
        videoTime=event_input.video_time,
        similarity=max(0.0, min(1.0, event_input.similarity)),
        createdAt=now,
    )
    payload = f"event: face-event\ndata: {event.model_dump_json()}\n\n"
    with state.event_lock:
        state.events_store.insert(0, event)
        del state.events_store[EVENTS_STORE_MAX_SIZE:]
    broadcast_event(payload)

    try:
        cam_obj = camera_cache.get(event_input.camera_id)
        camera_area = cam_obj.area if cam_obj else None
        with SessionLocal() as pgdb:
            row = FaceMatchEventORM(
                deployment_task_id=event_input.deployment_task_id,
                face_profile_id=event_input.face_profile_id,
                face_profile_name=event_input.profile_name,
                face_profile_photo_url=event_input.face_photo_url,
                snapshot_url=snapshot_url,
                camera_id=event_input.camera_id,
                camera_name=event_input.camera_name,
                camera_area=camera_area,
                similarity=max(0.0, min(1.0, event_input.similarity)),
                matched_at=event_input.video_time if isinstance(event_input.video_time, datetime) else now,
            )
            pgdb.add(row)
            pgdb.commit()
    except SQLAlchemyError as exc:  # 数据库不可达不阻断事件主流程（与重构前一致）
        logger.error("FaceMatchEventORM insert failed: %s", exc)

    return event


def recent_duplicate_event(camera_id: UUID, profile_id: UUID, task_id: UUID | None = None) -> bool:
    """判断冷却期内是否已有同人同机（或同任务）事件。

    Args:
        camera_id: 摄像头 ID。
        profile_id: 人脸档案 ID。
        task_id: 布控任务 ID（提供时额外查库去重）。

    Returns:
        冷却期内存在重复事件返回 True。
    """
    cooldown_seconds = get_settings().face_event_cooldown_seconds
    cutoff = time.time() - cooldown_seconds
    with state.event_lock:
        for event in state.events_store:
            if (
                event.cameraId == camera_id
                and event.faceProfileId == profile_id
                and event.createdAt.timestamp() >= cutoff
            ):
                return True
    if task_id is not None:
        try:
            with SessionLocal() as pgdb:
                recent = (
                    pgdb.query(FaceMatchEventORM)
                    .filter(
                        FaceMatchEventORM.camera_id == camera_id,
                        FaceMatchEventORM.face_profile_id == profile_id,
                        FaceMatchEventORM.deployment_task_id == task_id,
                    )
                    .order_by(FaceMatchEventORM.matched_at.desc())
                    .first()
                )
                if recent is not None and recent.matched_at is not None:
                    age = (datetime.now(timezone.utc) - recent.matched_at).total_seconds()
                    if age < cooldown_seconds:
                        return True
        except (SQLAlchemyError, TypeError) as exc:  #  naive/aware datetime 混用时按不去重处理（与原宽捕获一致）
            logger.warning("recent duplicate check skipped: %s", exc)
    return False
