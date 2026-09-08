"""布控事件入库前去重：按"事件去重配置"规则判断事件是否需要存储。

规则来源为内存态 ``state.event_dedup_rules_store``（启动时从 event_dedup_rules
表载入，CRUD 实时维护）。匹配规则后按策略判定：

- 时间维度去重：同摄像头（人脸事件再同档案）同类型事件在时间窗内已存在则不存；
- 区间重叠图像去重：以最近一条已存事件为锚点，时间窗内的事件（除窗口首个外）
  直接丢弃不做图像比较；出窗后的首个事件与上一个已保存事件比较快照哈希，
  相似度达到阈值则丢弃——比纯时间窗更严格；
- 实时重叠图像去重：忽略时间长度，只与上一个已保存事件比较快照哈希，
  相似度达到阈值则不存。

去重只门控落库，不影响 SSE 实时推送与内存态事件队列。
"""

import base64
import binascii
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app import state
from app.models.deployment_event import DeploymentEventORM

logger = logging.getLogger(__name__)

STRATEGY_TIME_WINDOW = "时间维度去重"
STRATEGY_INTERVAL_IMAGE = "区间重叠图像去重"
STRATEGY_REALTIME_IMAGE = "实时重叠图像去重"


def compute_snapshot_hash(snapshot_base64: str | None) -> str | None:
    """计算快照的 64bit 均值感知哈希（aHash），非法数据返回 None。

    Args:
        snapshot_base64: base64 图片（可带 data URL 前缀），可为 None。

    Returns:
        16 位十六进制哈希字符串，或 None。
    """
    if not snapshot_base64:
        return None
    data = snapshot_base64
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        return None
    if not raw:
        return None
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    try:
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        small = cv2.resize(image, (8, 8), interpolation=cv2.INTER_AREA)
        mean = float(small.mean())
        bits = 0
        for value in small.flatten():
            bits = (bits << 1) | int(value >= mean)
        return f"{bits:016x}"
    except (cv2.error, ValueError, TypeError) as exc:  # 哈希失败不阻断事件主流程
        logger.warning("snapshot hash compute failed: %s", exc)
        return None


def hash_similarity(hash_a: str, hash_b: str) -> float:
    """两个 64bit 十六进制哈希的相似度（1 - 汉明距离/64）。"""
    try:
        bits_a = int(hash_a, 16)
        bits_b = int(hash_b, 16)
    except ValueError:
        return 0.0
    distance = bin(bits_a ^ bits_b).count("1")
    return 1.0 - distance / 64.0


def _rule_matches_scope(rule: dict[str, Any], camera_id: UUID | None, camera_name: str | None) -> bool:
    """判断规则的摄像头作用域是否覆盖当前事件。"""
    if bool(rule.get("all_cameras", True)):
        return True
    cameras = {str(item) for item in (rule.get("cameras") or [])}
    return str(camera_id) in cameras or (camera_name or "") in cameras


def _rule_matches_algorithm(rule: dict[str, Any], event_type: str) -> bool:
    """判断规则的算法标识是否匹配当前事件类型（空 = 适用全部）。"""
    algorithm = str(rule.get("algorithm") or "").strip()
    if not algorithm:
        return True
    return algorithm.lower() == event_type.lower()


def _duplicate_in_time_window(
    db: Session,
    *,
    camera_id: UUID | None,
    event_type: str,
    face_profile_id: UUID | None,
    occurred_at: datetime,
    duration_minutes: int,
) -> bool:
    """时间窗内是否已存在同摄像头同类型（人脸事件同档案）的已存事件。"""
    cutoff = occurred_at - timedelta(minutes=duration_minutes)
    query = db.query(DeploymentEventORM).filter(
        DeploymentEventORM.camera_id == camera_id,
        DeploymentEventORM.event_type == event_type,
        DeploymentEventORM.occurred_at >= cutoff,
    )
    if face_profile_id is not None:
        query = query.filter(DeploymentEventORM.face_profile_id == face_profile_id)
    return db.query(query.exists()).scalar() is True


def _as_aware(dt: datetime) -> datetime:
    """naive 时间按 UTC 处理，避免与 tz-aware 时间相减报错。"""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _last_saved_event(
    db: Session,
    *,
    camera_id: UUID | None,
    event_type: str,
) -> tuple[datetime, str | None] | None:
    """同摄像头同类型的最近一条已存事件（occurred_at, snapshot_hash），无则 None。"""
    row = (
        db.query(DeploymentEventORM.occurred_at, DeploymentEventORM.snapshot_hash)
        .filter(
            DeploymentEventORM.camera_id == camera_id,
            DeploymentEventORM.event_type == event_type,
        )
        .order_by(DeploymentEventORM.occurred_at.desc())
        .first()
    )
    return (row[0], row[1]) if row else None


def _duplicate_by_interval_image(
    db: Session,
    *,
    camera_id: UUID | None,
    event_type: str,
    occurred_at: datetime,
    duration_minutes: int,
    snapshot_hash: str | None,
    threshold: float,
) -> bool:
    """区间重叠图像去重：窗口内事件直接丢弃，出窗首个事件与上一个已存事件比相似度。

    窗口锚点为最近一条已存事件。窗口内（含边界）的事件不比较截图直接判重；
    出窗后的首个事件与上一个已保存事件比较快照哈希，相似度达阈值判重。
    """
    last = _last_saved_event(db, camera_id=camera_id, event_type=event_type)
    if last is None:
        return False
    last_occurred, last_hash = last
    if _as_aware(occurred_at) - _as_aware(last_occurred) <= timedelta(minutes=duration_minutes):
        return True
    if snapshot_hash is None or last_hash is None:
        return False
    return hash_similarity(snapshot_hash, last_hash) >= threshold


def _duplicate_with_last_image(
    db: Session,
    *,
    camera_id: UUID | None,
    event_type: str,
    snapshot_hash: str | None,
    threshold: float,
) -> bool:
    """实时重叠图像去重：忽略时间长度，只与上一个已保存事件比较快照相似度。"""
    if snapshot_hash is None:
        return False
    last = _last_saved_event(db, camera_id=camera_id, event_type=event_type)
    if last is None or last[1] is None:
        return False
    return hash_similarity(snapshot_hash, last[1]) >= threshold


def passes_dedup_rules(
    db: Session,
    *,
    camera_id: UUID | None,
    camera_name: str | None,
    event_type: str,
    face_profile_id: UUID | None = None,
    occurred_at: datetime,
    snapshot_hash: str | None = None,
) -> bool:
    """按事件去重配置判断事件是否应入库。

    Args:
        db: 数据库会话。
        camera_id: 事件摄像头 ID。
        camera_name: 事件摄像头名称（规则 cameras 列表可能按名称配置）。
        event_type: 事件类别（face_match / object_detection / worker 上报的 eventType）。
        face_profile_id: 人脸档案 ID（人脸事件用于同人判定）。
        occurred_at: 事件发生时间。
        snapshot_hash: 快照感知哈希（图像去重策略使用）。

    Returns:
        通过全部匹配规则（或无匹配规则）返回 True，命中任一规则去重则返回 False。
    """
    for rule in list(state.event_dedup_rules_store.values()):
        if not bool(rule.get("enabled", True)):
            continue
        if not _rule_matches_scope(rule, camera_id, camera_name):
            continue
        if not _rule_matches_algorithm(rule, event_type):
            continue
        strategy = str(rule.get("strategy") or STRATEGY_TIME_WINDOW)
        if strategy == STRATEGY_TIME_WINDOW:
            duration = rule.get("duration_minutes")
            if duration is None:
                continue
            if _duplicate_in_time_window(
                db,
                camera_id=camera_id,
                event_type=event_type,
                face_profile_id=face_profile_id,
                occurred_at=occurred_at,
                duration_minutes=int(duration),
            ):
                return False
        elif strategy == STRATEGY_INTERVAL_IMAGE:
            duration = rule.get("duration_minutes")
            threshold = rule.get("similarity")
            if duration is None or threshold is None:
                continue
            if _duplicate_by_interval_image(
                db,
                camera_id=camera_id,
                event_type=event_type,
                occurred_at=occurred_at,
                duration_minutes=int(duration),
                snapshot_hash=snapshot_hash,
                threshold=float(threshold),
            ):
                return False
        elif strategy == STRATEGY_REALTIME_IMAGE:
            threshold = rule.get("similarity")
            if threshold is None:
                continue
            if _duplicate_with_last_image(
                db,
                camera_id=camera_id,
                event_type=event_type,
                snapshot_hash=snapshot_hash,
                threshold=float(threshold),
            ):
                return False
    return True
