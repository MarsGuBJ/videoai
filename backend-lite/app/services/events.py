"""事件总线：人脸/目标事件的创建、去重、入库与 SSE 广播。"""

import logging
import queue
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models.deployment_event import DeploymentEventORM
from app.schemas.event import FaceEventResponse, ObjectEventResponse, ObjectInfo
from app.services import camera_cache
from app.services.event_dedup import compute_snapshot_hash, passes_dedup_rules
from app.utils.assets import save_snapshot

logger = logging.getLogger(__name__)

EVENTS_STORE_MAX_SIZE = 200
EVENT_SUBSCRIBER_QUEUE_SIZE = 100
OBJECT_EVENT_COOLDOWN_SECONDS = 2.0

EVENT_TYPE_FACE_MATCH = "face_match"
EVENT_TYPE_OBJECT_DETECTION = "object_detection"


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


class ObjectEventInput(BaseModel):
    """create_object_event 的入参封装。"""

    camera_id: UUID
    camera_name: str
    objects: list[ObjectInfo]
    snapshot_base64: str | None = None
    video_time: datetime
    frame_width: int = 0
    frame_height: int = 0
    event_type: str | None = None
    deployment_task_id: UUID | None = None


def ensure_deployment_event_schema() -> None:
    """轻量迁移：为 deployment_events 补列（幂等）。"""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE deployment_events ADD COLUMN IF NOT EXISTS algorithm_code VARCHAR(100)")
            )
            conn.execute(
                text("ALTER TABLE deployment_events ADD COLUMN IF NOT EXISTS review_status VARCHAR(10)")
            )
    except SQLAlchemyError as exc:  # 数据库不可达时跳过迁移，不阻断启动
        logger.error("deployment event schema ensure failed: %s", exc)


def _task_algorithm_code(task_id: UUID | None) -> str | None:
    """从内存任务存储带出任务的 algorithmCode；任务缺失或未配置时返回 None。

    Args:
        task_id: 布控任务 ID，可为 None。

    Returns:
        任务的算法编号，取不到时为 None（不阻断事件主流程）。
    """
    if task_id is None:
        return None
    task = state.deployment_tasks_store.get(task_id)
    return task.algorithmCode if task else None


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


def _camera_area(camera_id: UUID) -> str | None:
    """从摄像头缓存解析区域，缓存未命中返回 None。"""
    cam_obj = camera_cache.get(camera_id)
    return cam_obj.area if cam_obj else None


def create_face_event(event_input: FaceEventInput) -> FaceEventResponse | None:
    """创建人脸事件：冷却去重、存快照、入内存队列、广播 SSE、按去重规则落库。

    Args:
        event_input: 事件入参封装。

    Returns:
        新建的事件；命中冷却去重时返回 None。
    """
    if recent_duplicate_event(event_input.camera_id, event_input.face_profile_id, event_input.deployment_task_id):
        return None
    now = datetime.now(timezone.utc)
    snapshot_url = save_snapshot(event_input.snapshot_base64)
    snapshot_hash = compute_snapshot_hash(event_input.snapshot_base64)
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

    occurred_at = event_input.video_time if isinstance(event_input.video_time, datetime) else now
    try:
        with SessionLocal() as pgdb:
            if not passes_dedup_rules(
                pgdb,
                camera_id=event_input.camera_id,
                camera_name=event_input.camera_name,
                event_type=EVENT_TYPE_FACE_MATCH,
                face_profile_id=event_input.face_profile_id,
                occurred_at=occurred_at,
                snapshot_hash=snapshot_hash,
            ):
                logger.info(
                    "face event skipped by dedup rules: camera=%s profile=%s",
                    event_input.camera_id,
                    event_input.face_profile_id,
                )
                return event
            row = DeploymentEventORM(
                deployment_task_id=event_input.deployment_task_id,
                event_type=EVENT_TYPE_FACE_MATCH,
                algorithm_code=_task_algorithm_code(event_input.deployment_task_id),
                face_profile_id=event_input.face_profile_id,
                face_profile_name=event_input.profile_name,
                face_profile_photo_url=event_input.face_photo_url,
                snapshot_url=snapshot_url,
                snapshot_hash=snapshot_hash,
                camera_id=event_input.camera_id,
                camera_name=event_input.camera_name,
                camera_area=_camera_area(event_input.camera_id),
                similarity=max(0.0, min(1.0, event_input.similarity)),
                occurred_at=occurred_at,
            )
            pgdb.add(row)
            pgdb.commit()
    except SQLAlchemyError as exc:  # 数据库不可达不阻断事件主流程（与重构前一致）
        logger.error("DeploymentEventORM insert failed: %s", exc)

    return event


def create_object_event(event_input: ObjectEventInput) -> ObjectEventResponse | None:
    """创建目标检测事件：同摄像头 2 秒冷却、入内存队列、广播 SSE、按去重规则落库。

    Args:
        event_input: 事件入参封装。

    Returns:
        新建的事件；冷却期内直接丢弃返回 None。
    """
    camera_key = str(event_input.camera_id)
    now_ts = time.time()
    with state.event_lock:
        last_time = state.object_event_cooldowns.get(camera_key, 0)
        if now_ts - last_time < OBJECT_EVENT_COOLDOWN_SECONDS:
            return None
        state.object_event_cooldowns[camera_key] = now_ts

    now = datetime.now(timezone.utc)
    snapshot_url = save_snapshot(event_input.snapshot_base64)
    snapshot_hash = compute_snapshot_hash(event_input.snapshot_base64)
    event_type = event_input.event_type or EVENT_TYPE_OBJECT_DETECTION
    event = ObjectEventResponse(
        id=uuid4(),
        cameraId=event_input.camera_id,
        cameraName=event_input.camera_name,
        objects=event_input.objects,
        snapshotUrl=snapshot_url,
        videoTime=event_input.video_time,
        frameWidth=event_input.frame_width,
        frameHeight=event_input.frame_height,
        eventType=event_input.event_type,
        deploymentTaskId=event_input.deployment_task_id,
        createdAt=now,
    )
    payload = f"event: object-event\ndata: {event.model_dump_json()}\n\n"
    with state.event_lock:
        state.object_events_store.insert(0, event)
        del state.object_events_store[EVENTS_STORE_MAX_SIZE:]
    broadcast_event(payload)

    occurred_at = event_input.video_time if isinstance(event_input.video_time, datetime) else now
    try:
        with SessionLocal() as pgdb:
            if not passes_dedup_rules(
                pgdb,
                camera_id=event_input.camera_id,
                camera_name=event_input.camera_name,
                event_type=event_type,
                occurred_at=occurred_at,
                snapshot_hash=snapshot_hash,
            ):
                logger.info("object event skipped by dedup rules: camera=%s", event_input.camera_id)
                return event
            row = DeploymentEventORM(
                deployment_task_id=event_input.deployment_task_id,
                event_type=event_type,
                algorithm_code=_task_algorithm_code(event_input.deployment_task_id),
                objects=[obj.model_dump() for obj in event_input.objects],
                frame_width=event_input.frame_width,
                frame_height=event_input.frame_height,
                snapshot_url=snapshot_url,
                snapshot_hash=snapshot_hash,
                camera_id=event_input.camera_id,
                camera_name=event_input.camera_name,
                camera_area=_camera_area(event_input.camera_id),
                occurred_at=occurred_at,
            )
            pgdb.add(row)
            pgdb.commit()
    except SQLAlchemyError as exc:  # 数据库不可达不阻断事件主流程
        logger.error("DeploymentEventORM insert failed: %s", exc)

    return event


def migrate_face_match_events() -> None:
    """Best-effort：把旧 face_match_events 表数据迁入 deployment_events（幂等，不删旧表）。

    旧表确认不再使用后可手工执行 ``DROP TABLE face_match_events;``。
    """
    try:
        with engine.begin() as conn:
            table_names = set(inspect(conn).get_table_names())
            if "face_match_events" not in table_names or "deployment_events" not in table_names:
                return
            result = conn.execute(
                text(
                    "INSERT INTO deployment_events ("
                    "id, deployment_task_id, event_type, face_profile_id, face_profile_name,"
                    " face_profile_photo_url, snapshot_url, camera_id, camera_name, camera_area,"
                    " similarity, frame_width, frame_height, occurred_at, created_at"
                    ") "
                    "SELECT id, deployment_task_id, 'face_match', face_profile_id, face_profile_name,"
                    " face_profile_photo_url, snapshot_url, camera_id, camera_name, camera_area,"
                    " similarity, 0, 0, matched_at, created_at "
                    "FROM face_match_events "
                    "WHERE id NOT IN (SELECT id FROM deployment_events)"
                )
            )
            if result.rowcount:
                logger.info("migrated %d face_match_events rows into deployment_events", result.rowcount)
    except SQLAlchemyError as exc:  # 数据库不可达或旧表结构异常时跳过迁移，不阻断启动
        logger.error("face_match_events migration failed: %s", exc)


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
                    pgdb.query(DeploymentEventORM)
                    .filter(
                        DeploymentEventORM.camera_id == camera_id,
                        DeploymentEventORM.face_profile_id == profile_id,
                        DeploymentEventORM.deployment_task_id == task_id,
                    )
                    .order_by(DeploymentEventORM.occurred_at.desc())
                    .first()
                )
                if recent is not None and recent.occurred_at is not None:
                    age = (datetime.now(timezone.utc) - recent.occurred_at).total_seconds()
                    if age < cooldown_seconds:
                        return True
        except (SQLAlchemyError, TypeError) as exc:  #  naive/aware datetime 混用时按不去重处理（与原宽捕获一致）
            logger.warning("recent duplicate check skipped: %s", exc)
    return False
