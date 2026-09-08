"""布控事件去重全链路测试：真实 ingest 路径 + 真实 sqlite 库验证三种去重策略。

与 test_deployment_events_api.py 不同，这里不打桩 passes_dedup_rules，
而是走 worker 上报布控事件的实际入口 create_object_event：
入内存队列 / SSE 广播 → passes_dedup_rules（真实规则判定）→ 落库门控。
"""

import base64
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import cv2
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.events as events_service
from app import state
from app.models.deployment_event import DeploymentEventORM
from app.schemas.event import ObjectInfo
from app.services.event_dedup import hash_similarity

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
CAMERA_ID = uuid4()


def _jpeg_b64(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _base_image() -> str:
    """带白色方块的固定图像。"""
    img = np.zeros((200, 200), dtype=np.uint8)
    img[50:150, 50:150] = 255
    return _jpeg_b64(img)


def _noise_image() -> str:
    """与固定图像明显不同的随机噪声图。"""
    rng = np.random.default_rng(42)
    return _jpeg_b64(rng.integers(0, 255, (200, 200), dtype=np.uint8))


BASE_SNAPSHOT = _base_image()
NOISE_SNAPSHOT = _noise_image()


@pytest.fixture()
def dedup_env(monkeypatch):
    """真实 sqlite 库 + 隔离的内存态规则，快照不落盘、关闭目标事件冷却。"""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    DeploymentEventORM.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    monkeypatch.setattr(events_service, "SessionLocal", session_factory)
    monkeypatch.setattr(events_service, "save_snapshot", lambda _: "/api/assets/snapshots/test.jpg")
    monkeypatch.setattr(events_service, "OBJECT_EVENT_COOLDOWN_SECONDS", 0.0)

    saved_rules = dict(state.event_dedup_rules_store)
    saved_cooldowns = dict(state.object_event_cooldowns)
    state.event_dedup_rules_store.clear()
    state.object_event_cooldowns.clear()
    try:
        yield session_factory
    finally:
        state.event_dedup_rules_store.clear()
        state.event_dedup_rules_store.update(saved_rules)
        state.object_event_cooldowns.clear()
        state.object_event_cooldowns.update(saved_cooldowns)
        engine.dispose()


def _add_rule(**overrides) -> dict:
    rule = {
        "id": f"rule-{uuid4()}",
        "name": "规则",
        "algorithm": "",
        "strategy": "时间维度去重",
        "duration_minutes": 10,
        "similarity": None,
        "all_cameras": True,
        "cameras": [],
        "remark": "",
        "enabled": True,
    }
    rule.update(overrides)
    state.event_dedup_rules_store[rule["id"]] = rule
    return rule


def _ingest(*, occurred_at: datetime, snapshot: str | None = None, camera_id=CAMERA_ID) -> None:
    """模拟 worker 上报一个布控目标检测事件。"""
    event_input = events_service.ObjectEventInput(
        camera_id=camera_id,
        camera_name="东门",
        objects=[ObjectInfo(labelId=1, labelName="person", score=0.9, x1=0, y1=0, x2=10, y2=10)],
        snapshot_base64=snapshot,
        video_time=occurred_at,
        deployment_task_id=uuid4(),
    )
    events_service.create_object_event(event_input)


def _stored_count(session_factory) -> int:
    with session_factory() as db:
        return db.query(DeploymentEventORM).count()


# ---------------- 时间维度去重 ----------------


def test_time_window_strategy_dedups_within_duration_ignoring_similarity(dedup_env):
    """时间维度去重：时长内只存一个事件，与截图/相似度无关。"""
    _add_rule(strategy="时间维度去重", duration_minutes=10, similarity=None)

    _ingest(occurred_at=T0, snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 1

    # 5 分钟后，截图完全不同（随机噪声），仍被时间窗去重 → 证明相似度字段被忽略
    _ingest(occurred_at=T0 + timedelta(minutes=5), snapshot=NOISE_SNAPSHOT)
    assert _stored_count(dedup_env) == 1

    # 超出 10 分钟时长后放行
    _ingest(occurred_at=T0 + timedelta(minutes=11), snapshot=NOISE_SNAPSHOT)
    assert _stored_count(dedup_env) == 2


def test_time_window_strategy_scoped_per_camera(dedup_env):
    """时间窗按摄像头隔离：另一摄像头的事件不受影响。"""
    _add_rule(strategy="时间维度去重", duration_minutes=10)

    _ingest(occurred_at=T0, snapshot=BASE_SNAPSHOT)
    _ingest(occurred_at=T0 + timedelta(minutes=1), snapshot=BASE_SNAPSHOT, camera_id=uuid4())
    assert _stored_count(dedup_env) == 2


# ---------------- 区间重叠图像去重 ----------------


def test_interval_image_strategy_window_then_similarity(dedup_env):
    """区间重叠图像去重：窗口内除首个外都丢弃（不比图）；出窗首个事件与上一个已存事件比相似度。"""
    _add_rule(strategy="区间重叠图像去重", duration_minutes=10, similarity=0.9)

    _ingest(occurred_at=T0, snapshot=NOISE_SNAPSHOT)  # 窗口首个事件，保留
    assert _stored_count(dedup_env) == 1

    # 窗口内：截图完全不同也不做比较，直接丢弃
    _ingest(occurred_at=T0 + timedelta(minutes=5), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 1

    # 出窗首个事件：与上一个保存事件（NOISE）相同 → 丢弃（纯时间窗策略此处会保留，更严格）
    _ingest(occurred_at=T0 + timedelta(minutes=11), snapshot=NOISE_SNAPSHOT)
    assert _stored_count(dedup_env) == 1

    # 出窗事件：与上一个保存事件不相似 → 保留，成为新的窗口锚点
    _ingest(occurred_at=T0 + timedelta(minutes=12), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 2

    # 新窗口内的事件再次直接丢弃
    _ingest(occurred_at=T0 + timedelta(minutes=13), snapshot=NOISE_SNAPSHOT)
    assert _stored_count(dedup_env) == 2


# ---------------- 实时重叠图像去重 ----------------


def test_realtime_image_strategy_filters_by_similarity_ignoring_time(dedup_env):
    """实时重叠图像去重：忽略时间长度，与历史事件截图比较，相似度达阈值则去重。"""
    _add_rule(strategy="实时重叠图像去重", duration_minutes=None, similarity=0.9)

    _ingest(occurred_at=T0, snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 1

    # 相隔很久的相同截图仍被去重 → 时间长度被忽略
    _ingest(occurred_at=T0 + timedelta(hours=5), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 1

    # 不相似截图放行
    _ingest(occurred_at=T0 + timedelta(hours=5, minutes=1), snapshot=NOISE_SNAPSHOT)
    assert _stored_count(dedup_env) == 2


def test_realtime_image_strategy_compares_only_with_last_saved(dedup_env):
    """实时重叠图像去重只与上一个保存事件比较，更早的相似历史不影响判定。"""
    _add_rule(strategy="实时重叠图像去重", duration_minutes=None, similarity=0.9)

    _ingest(occurred_at=T0, snapshot=BASE_SNAPSHOT)
    _ingest(occurred_at=T0 + timedelta(hours=1), snapshot=NOISE_SNAPSHOT)  # 与 BASE 不同 → 保留
    assert _stored_count(dedup_env) == 2

    # 与上一个保存事件（NOISE）不同 → 保留，尽管与最早的事件（BASE）相同
    _ingest(occurred_at=T0 + timedelta(hours=2), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 3

    # 与上一个保存事件（BASE）相同 → 丢弃
    _ingest(occurred_at=T0 + timedelta(hours=3), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 3


# ---------------- 无规则 / 停用规则 ----------------


def test_no_rule_stores_every_event(dedup_env):
    _ingest(occurred_at=T0, snapshot=BASE_SNAPSHOT)
    _ingest(occurred_at=T0 + timedelta(seconds=10), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 2


def test_disabled_rule_does_not_filter(dedup_env):
    _add_rule(strategy="时间维度去重", duration_minutes=10, enabled=False)

    _ingest(occurred_at=T0, snapshot=BASE_SNAPSHOT)
    _ingest(occurred_at=T0 + timedelta(minutes=1), snapshot=BASE_SNAPSHOT)
    assert _stored_count(dedup_env) == 2


# ---------------- 相似度计算 ----------------


def test_snapshot_hash_similarity_semantics():
    """相同图相似度 1.0，噪声图与固定图相似度显著低于 0.9 阈值。"""
    from app.services.event_dedup import compute_snapshot_hash

    hash_base = compute_snapshot_hash(BASE_SNAPSHOT)
    hash_base_again = compute_snapshot_hash(_base_image())
    hash_noise = compute_snapshot_hash(NOISE_SNAPSHOT)

    assert hash_base is not None and hash_noise is not None
    assert hash_similarity(hash_base, hash_base_again) == 1.0
    assert hash_similarity(hash_base, hash_noise) < 0.9
