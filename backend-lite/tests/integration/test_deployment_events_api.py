"""布控事件接口契约测试：分页/汇总在路由模块命名空间 mock 服务函数，落库路径用假会话。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app.api.routers.events as events_router
import app.services.events as events_service
from app import state
from app.schemas.deployment_task import DeploymentTaskResponse
from app.schemas.event import (
    DeploymentEventAreaItem,
    DeploymentEventItem,
    DeploymentEventReviewItem,
    DeploymentEventStats,
    DeploymentEventSummary,
    DeploymentEventTrendItem,
)

OCCURRED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _sample_item(**overrides) -> DeploymentEventItem:
    payload = {
        "id": uuid4(),
        "deploymentTaskId": uuid4(),
        "eventType": "face_match",
        "algorithmCode": "algo-gather-v1",
        "reviewStatus": "有效",
        "faceProfileId": uuid4(),
        "faceProfileName": "张三",
        "faceProfilePhotoUrl": "/api/assets/faces/p1.jpg",
        "snapshotUrl": "/api/assets/snapshots/s1.jpg",
        "cameraId": uuid4(),
        "cameraName": "东门",
        "cameraArea": "园区",
        "similarity": 0.87,
        "occurredAt": OCCURRED_AT,
        "createdAt": OCCURRED_AT,
    }
    payload.update(overrides)
    return DeploymentEventItem(**payload)


class _FakeSession:
    """记录 add/commit 的假数据库会话。"""

    def __init__(self):
        self.added: list = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.commits += 1


def _object_payload(**overrides) -> dict:
    payload = {
        "cameraId": str(uuid4()),
        "cameraName": "东门",
        "objects": [{"labelId": 1, "labelName": "person", "score": 0.9, "x1": 0, "y1": 0, "x2": 10, "y2": 10}],
        "videoTime": "2026-01-01T00:00:00Z",
    }
    payload.update(overrides)
    return payload


# ---------------- GET /api/deployment-events ----------------


def test_list_deployment_events_returns_paged_camel_case(client: TestClient, monkeypatch):
    item = _sample_item()
    monkeypatch.setattr(events_router, "query_deployment_events", lambda **kwargs: ([item], 1))

    response = client.get("/api/deployment-events?page=1&size=10")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 10
    assert len(body["items"]) == 1
    first = body["items"][0]
    assert first["eventType"] == "face_match"
    assert first["algorithmCode"] == "algo-gather-v1"
    assert first["reviewStatus"] == "有效"
    assert first["faceProfileName"] == "张三"
    assert first["cameraArea"] == "园区"
    assert first["occurredAt"] is not None


def test_list_deployment_events_clamps_page_and_size(client: TestClient, monkeypatch):
    captured: dict = {}

    def fake_query(**kwargs):
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(events_router, "query_deployment_events", fake_query)

    response = client.get("/api/deployment-events?page=0&size=500")

    assert response.status_code == 200
    assert captured["page"] == 1
    assert captured["size"] == 100


def test_list_deployment_events_passes_filters(client: TestClient, monkeypatch):
    captured: dict = {}

    def fake_query(**kwargs):
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(events_router, "query_deployment_events", fake_query)
    task_id = str(uuid4())

    response = client.get(
        f"/api/deployment-events?taskId={task_id}&eventType=face_match&keyword=张"
        "&startTime=2026-01-01T00:00:00Z&endTime=2026-01-02T00:00:00Z"
    )

    assert response.status_code == 200
    assert str(captured["task_id"]) == task_id
    assert captured["event_type"] == "face_match"
    assert captured["keyword"] == "张"
    assert captured["start_time"] is not None
    assert captured["end_time"] is not None


def test_list_deployment_events_db_error_returns_empty_page(client: TestClient, monkeypatch):
    def broken_query(**kwargs):
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(events_router, "query_deployment_events", broken_query)

    response = client.get("/api/deployment-events")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}


# ---------------- GET /api/deployment-events/summary ----------------


def test_deployment_events_summary_returns_counts(client: TestClient, monkeypatch):
    summary = DeploymentEventSummary(total=8, today=3, faceMatch=5, objectDetection=3)
    monkeypatch.setattr(events_router, "deployment_events_summary", lambda: summary)

    response = client.get("/api/deployment-events/summary")

    assert response.status_code == 200
    assert response.json() == {"total": 8, "today": 3, "faceMatch": 5, "objectDetection": 3}


def test_deployment_events_summary_db_error_returns_zeros(client: TestClient, monkeypatch):
    def broken_summary():
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(events_router, "deployment_events_summary", broken_summary)

    response = client.get("/api/deployment-events/summary")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "today": 0, "faceMatch": 0, "objectDetection": 0}


# ---------------- GET /api/deployment-events/stats ----------------


def _sample_stats() -> DeploymentEventStats:
    return DeploymentEventStats(
        total=12,
        today=3,
        week=9,
        unreviewed=4,
        reviewRate=0.75,
        faceMatch=7,
        objectDetection=5,
        areas=["园区", "仓储区"],
        trend=[
            DeploymentEventTrendItem(date="2026-01-01", count=5),
            DeploymentEventTrendItem(date="2026-01-02", count=7),
        ],
        byArea=[DeploymentEventAreaItem(area="园区", count=8), DeploymentEventAreaItem(area="仓储区", count=4)],
        reviewByType=[
            DeploymentEventReviewItem(eventType="face_match", valid=4, invalid=1, unreviewed=2),
            DeploymentEventReviewItem(eventType="object_detection", valid=2, invalid=1, unreviewed=2),
        ],
    )


def test_deployment_events_stats_returns_camel_case(client: TestClient, monkeypatch):
    monkeypatch.setattr(events_router, "deployment_events_stats", lambda **kwargs: _sample_stats())

    response = client.get("/api/deployment-events/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 12
    assert body["reviewRate"] == 0.75
    assert body["areas"] == ["园区", "仓储区"]
    assert body["trend"][0] == {"date": "2026-01-01", "count": 5}
    assert body["byArea"][0] == {"area": "园区", "count": 8}
    assert body["reviewByType"][0] == {"eventType": "face_match", "valid": 4, "invalid": 1, "unreviewed": 2}


def test_deployment_events_stats_passes_filters(client: TestClient, monkeypatch):
    captured: dict = {}

    def fake_stats(**kwargs):
        captured.update(kwargs)
        return _sample_stats()

    monkeypatch.setattr(events_router, "deployment_events_stats", fake_stats)

    response = client.get(
        "/api/deployment-events/stats?startTime=2026-01-01T00:00:00Z&endTime=2026-01-07T00:00:00Z&area=园区"
    )

    assert response.status_code == 200
    assert captured["start_time"] is not None
    assert captured["end_time"] is not None
    assert captured["area"] == "园区"


def test_deployment_events_stats_db_error_returns_zeroed(client: TestClient, monkeypatch):
    def broken_stats(**kwargs):
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(events_router, "deployment_events_stats", broken_stats)

    response = client.get("/api/deployment-events/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["reviewRate"] == 0.0
    assert body["trend"] == []
    assert body["byArea"] == []
    assert body["reviewByType"] == []


# ---------------- 摄取落库门控 ----------------


def test_object_ingest_persists_when_dedup_passes(client: TestClient, monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(events_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(events_service, "passes_dedup_rules", lambda *args, **kwargs: True)

    response = client.post("/api/events/object-ingest", json=_object_payload())

    assert response.status_code == 200
    assert len(fake_session.added) == 1
    row = fake_session.added[0]
    assert row.event_type == "object_detection"
    assert row.objects[0]["labelName"] == "person"
    assert fake_session.commits == 1


def test_object_ingest_skips_storage_when_dedup_blocks(client: TestClient, monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(events_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(events_service, "passes_dedup_rules", lambda *args, **kwargs: False)

    response = client.post("/api/events/object-ingest", json=_object_payload())

    assert response.status_code == 200  # 实时事件照常返回，仅不落库
    assert fake_session.added == []
    assert fake_session.commits == 0


def test_face_ingest_persists_face_match_row(client: TestClient, monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(events_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(events_service, "passes_dedup_rules", lambda *args, **kwargs: True)
    payload = {
        "cameraId": str(uuid4()),
        "faceProfileId": str(uuid4()),
        "cameraName": "东门",
        "profileName": "张三",
        "facePhotoPath": "/api/assets/faces/p1.jpg",
        "videoTime": "2026-01-01T00:00:00Z",
        "similarity": 0.87,
    }

    response = client.post("/api/events/ingest", json=payload)

    assert response.status_code == 200
    assert len(fake_session.added) == 1
    row = fake_session.added[0]
    assert row.event_type == "face_match"
    assert row.face_profile_name == "张三"
    assert row.similarity == 0.87


# ---------------- 事件落库带出任务 algorithmCode ----------------


def _seed_task(**overrides) -> DeploymentTaskResponse:
    """在内存任务存储放一个带 algorithmCode 的布控任务。"""
    task = DeploymentTaskResponse(
        id=uuid4(),
        name="东门布控",
        pipeline="人脸识别流程",
        area="园区",
        areaCount=1,
        enabled=True,
        taskStatus="running",
        desc="",
        cameraIds=[],
        algorithmCode="algo-gather-v1",
        createdAt=OCCURRED_AT,
        updatedAt=OCCURRED_AT,
        **overrides,
    )
    state.deployment_tasks_store[task.id] = task
    return task


def test_object_ingest_writes_task_algorithm_code(client: TestClient, monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(events_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(events_service, "passes_dedup_rules", lambda *args, **kwargs: True)
    task = _seed_task()

    response = client.post("/api/events/object-ingest", json=_object_payload(deploymentTaskId=str(task.id)))

    assert response.status_code == 200
    assert len(fake_session.added) == 1
    assert fake_session.added[0].algorithm_code == "algo-gather-v1"


def test_object_ingest_unknown_task_writes_none_algorithm_code(client: TestClient, monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(events_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(events_service, "passes_dedup_rules", lambda *args, **kwargs: True)

    response = client.post("/api/events/object-ingest", json=_object_payload(deploymentTaskId=str(uuid4())))

    assert response.status_code == 200
    assert len(fake_session.added) == 1
    assert fake_session.added[0].algorithm_code is None


def test_face_ingest_writes_task_algorithm_code(client: TestClient, monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr(events_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(events_service, "passes_dedup_rules", lambda *args, **kwargs: True)
    # 冷却查库不在本测试关注范围内，直接判定为不重复（避免假会话无 query 能力）
    monkeypatch.setattr(events_service, "recent_duplicate_event", lambda *args, **kwargs: False)
    task = _seed_task()
    payload = {
        "cameraId": str(uuid4()),
        "faceProfileId": str(uuid4()),
        "cameraName": "东门",
        "profileName": "张三",
        "facePhotoPath": "/api/assets/faces/p1.jpg",
        "videoTime": "2026-01-01T00:00:00Z",
        "similarity": 0.87,
        "deploymentTaskId": str(task.id),
    }

    response = client.post("/api/events/ingest", json=payload)

    assert response.status_code == 200
    assert len(fake_session.added) == 1
    assert fake_session.added[0].algorithm_code == "algo-gather-v1"
