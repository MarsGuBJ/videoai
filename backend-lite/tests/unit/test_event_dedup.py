"""事件去重规则判定（passes_dedup_rules）单元测试：DB 查询用 MagicMock 打桩。"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app import state
from app.services.event_dedup import (
    compute_snapshot_hash,
    hash_similarity,
    passes_dedup_rules,
)

CAMERA_ID = uuid4()
OCCURRED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def dedup_store():
    """隔离去重规则内存态。"""
    saved = dict(state.event_dedup_rules_store)
    state.event_dedup_rules_store.clear()
    try:
        yield state.event_dedup_rules_store
    finally:
        state.event_dedup_rules_store.clear()
        state.event_dedup_rules_store.update(saved)


def _add_rule(store, **overrides):
    rule = {
        "id": "rule-1",
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
    store[rule["id"]] = rule
    return rule


def _mock_db(*, time_duplicate: bool = False, last_event: tuple | None = None) -> MagicMock:
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.scalar.return_value = time_duplicate
    query.all.return_value = [last_event] if last_event else []
    query.first.return_value = last_event
    return db


def _passes(db, **overrides):
    kwargs = {
        "camera_id": CAMERA_ID,
        "camera_name": "东门",
        "event_type": "face_match",
        "face_profile_id": uuid4(),
        "occurred_at": OCCURRED_AT,
        "snapshot_hash": None,
    }
    kwargs.update(overrides)
    return passes_dedup_rules(db, **kwargs)


def test_no_rules_allows_storage(dedup_store):
    assert _passes(_mock_db(time_duplicate=True)) is True


def test_disabled_rule_ignored(dedup_store):
    _add_rule(dedup_store, enabled=False)

    assert _passes(_mock_db(time_duplicate=True)) is True


def test_time_window_duplicate_blocks(dedup_store):
    _add_rule(dedup_store)

    assert _passes(_mock_db(time_duplicate=True)) is False


def test_time_window_no_duplicate_allows(dedup_store):
    _add_rule(dedup_store)

    assert _passes(_mock_db(time_duplicate=False)) is True


def test_camera_scope_mismatch_ignores_rule(dedup_store):
    _add_rule(dedup_store, all_cameras=False, cameras=["cam-other"])

    assert _passes(_mock_db(time_duplicate=True)) is True


def test_camera_scope_match_by_name_applies_rule(dedup_store):
    _add_rule(dedup_store, all_cameras=False, cameras=["东门"])

    assert _passes(_mock_db(time_duplicate=True)) is False


def test_algorithm_mismatch_ignores_rule(dedup_store):
    _add_rule(dedup_store, algorithm="smoke")

    assert _passes(_mock_db(time_duplicate=True), event_type="face_match") is True


def test_algorithm_match_applies_rule(dedup_store):
    _add_rule(dedup_store, algorithm="smoke")

    assert _passes(_mock_db(time_duplicate=True), event_type="smoke") is False


def test_time_window_without_duration_ignored(dedup_store):
    _add_rule(dedup_store, duration_minutes=None)

    assert _passes(_mock_db(time_duplicate=True)) is True


def test_realtime_image_blocks_when_last_event_similar(dedup_store):
    _add_rule(dedup_store, strategy="实时重叠图像去重", duration_minutes=None, similarity=0.9)

    last = (OCCURRED_AT - timedelta(hours=5), "ffffffffffffffff")
    db = _mock_db(last_event=last)
    assert _passes(db, snapshot_hash="ffffffffffffffff") is False


def test_realtime_image_allows_when_last_event_dissimilar(dedup_store):
    _add_rule(dedup_store, strategy="实时重叠图像去重", duration_minutes=None, similarity=0.9)

    last = (OCCURRED_AT - timedelta(minutes=1), "0000000000000000")
    db = _mock_db(last_event=last)
    assert _passes(db, snapshot_hash="ffffffffffffffff") is True


def test_realtime_image_allows_without_history(dedup_store):
    _add_rule(dedup_store, strategy="实时重叠图像去重", duration_minutes=None, similarity=0.9)

    assert _passes(_mock_db(last_event=None), snapshot_hash="ffffffffffffffff") is True


def test_realtime_image_allows_without_snapshot_hash(dedup_store):
    _add_rule(dedup_store, strategy="实时重叠图像去重", duration_minutes=None, similarity=0.9)

    last = (OCCURRED_AT - timedelta(minutes=1), "ffffffffffffffff")
    assert _passes(_mock_db(last_event=last), snapshot_hash=None) is True


def test_interval_image_within_window_blocks_without_comparing(dedup_store):
    """窗口内事件不比较截图直接丢弃，即使截图完全不同。"""
    _add_rule(dedup_store, strategy="区间重叠图像去重", duration_minutes=10, similarity=0.9)

    last = (OCCURRED_AT - timedelta(minutes=5), "0000000000000000")
    db = _mock_db(last_event=last)
    assert _passes(db, snapshot_hash="ffffffffffffffff") is False


def test_interval_image_out_of_window_similar_blocks(dedup_store):
    """出窗首个事件与上一个已存事件相似则丢弃（比纯时间窗更严格）。"""
    _add_rule(dedup_store, strategy="区间重叠图像去重", duration_minutes=10, similarity=0.9)

    last = (OCCURRED_AT - timedelta(minutes=11), "ffffffffffffffff")
    db = _mock_db(last_event=last)
    assert _passes(db, snapshot_hash="ffffffffffffffff") is False


def test_interval_image_out_of_window_dissimilar_allows(dedup_store):
    _add_rule(dedup_store, strategy="区间重叠图像去重", duration_minutes=10, similarity=0.9)

    last = (OCCURRED_AT - timedelta(minutes=11), "0000000000000000")
    db = _mock_db(last_event=last)
    assert _passes(db, snapshot_hash="ffffffffffffffff") is True


def test_interval_image_without_duration_ignored(dedup_store):
    _add_rule(dedup_store, strategy="区间重叠图像去重", duration_minutes=None, similarity=0.9)

    last = (OCCURRED_AT - timedelta(minutes=1), "ffffffffffffffff")
    assert _passes(_mock_db(last_event=last), snapshot_hash="ffffffffffffffff") is True


def test_hash_similarity_identical_is_one():
    assert hash_similarity("ffffffffffffffff", "ffffffffffffffff") == pytest.approx(1.0)


def test_hash_similarity_opposite_is_zero():
    assert hash_similarity("0000000000000000", "ffffffffffffffff") == pytest.approx(0.0)


def test_compute_snapshot_hash_none_and_garbage():
    assert compute_snapshot_hash(None) is None
    assert compute_snapshot_hash("not-valid-base64!!!") is None


def test_compute_snapshot_hash_real_image():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    image = np.zeros((32, 32), dtype=np.uint8)
    image[:, 16:] = 255
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok

    digest = compute_snapshot_hash(base64.b64encode(encoded.tobytes()).decode("ascii"))

    assert digest is not None
    assert len(digest) == 16
    int(digest, 16)
