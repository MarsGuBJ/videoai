"""定时复核任务路由与调度执行契约测试：TestClient 直连，DB 落库与大模型调用在测试中 mock。"""

import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.review_schedules as review_schedules_router
import app.services.review_schedules as review_schedules_service
from app import state
from app.core.config import get_settings

FAKE_IMAGE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
SNAPSHOT_URL = "/api/assets/snapshots/fake.jpg"

REVIEW_TYPE_ID = str(uuid4())
LLM_CONFIG_ID = str(uuid4())

REVIEW_TYPE_RECORD = {
    "id": REVIEW_TYPE_ID,
    "name": "人员跌倒",
    "code": "person_fall",
    "prompt": "请判断画面中是否有人跌倒",
    "inject_event": "",
    "remark": "",
    "llm_config_id": LLM_CONFIG_ID,
}
LLM_CONFIG_RECORD = {
    "id": LLM_CONFIG_ID,
    "name": "本地 Qwen-VL",
    "base_url": "http://localhost:9999/v1",
    "api_key": "",
    "deploy_type": "local",
    "timeout": 30,
    "temperature": 0.0,
    "max_tokens": 1024,
    "fps": 1,
}

CREATE_PAYLOAD = {
    "name": "每小时复核跌倒事件",
    "reviewTypeId": REVIEW_TYPE_ID,
    "cron": "0 * * * *",
    "enabled": True,
    "batchSize": 20,
}


def _seed_stores() -> None:
    state.review_types_store[REVIEW_TYPE_ID] = dict(REVIEW_TYPE_RECORD)
    state.llm_configs_store[LLM_CONFIG_ID] = dict(LLM_CONFIG_RECORD)


def _create_review_schedule(client: TestClient, monkeypatch, **overrides) -> dict:
    _seed_stores()
    monkeypatch.setattr(review_schedules_router, "persist_review_schedule", lambda record: None)
    payload = {**CREATE_PAYLOAD, **overrides}
    response = client.post("/api/review-schedules", json=payload)
    assert response.status_code == 200
    return response.json()


def _wait_last_result(schedule_id: str, timeout: float = 5.0) -> str:
    """轮询等待后台执行写入 last_result。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = state.review_schedules_store.get(schedule_id)
        if record and record.get("last_result"):
            return str(record["last_result"])
        time.sleep(0.05)
    raise AssertionError("timed out waiting for schedule last_result")


# ---------------- CRUD ----------------


def test_list_review_schedules_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/review-schedules")

    assert response.status_code == 200
    assert response.json() == []


def test_create_then_list_contains_created_record(client: TestClient, monkeypatch):
    created = _create_review_schedule(client, monkeypatch)

    assert created["id"]
    assert created["name"] == "每小时复核跌倒事件"
    assert created["cron"] == "0 * * * *"
    assert created["enabled"] is True
    assert created["batchSize"] == 20
    # 快照字段取自创建时的复核类型
    assert created["reviewTypeId"] == REVIEW_TYPE_ID
    assert created["reviewTypeName"] == "人员跌倒"
    assert created["reviewTypeCode"] == "person_fall"
    assert created["lastRunAt"] is None
    assert created["lastResult"] == ""
    assert created["createdAt"]
    assert created["updatedAt"]

    listed = client.get("/api/review-schedules").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


def test_create_review_schedule_defaults_enabled_and_batch_size(client: TestClient, monkeypatch):
    monkeypatch.setattr(review_schedules_router, "persist_review_schedule", lambda record: None)
    _seed_stores()
    # 缺省 enabled/batchSize 字段落为默认 True / 50
    payload = {"name": "默认参数", "reviewTypeId": REVIEW_TYPE_ID, "cron": "*/5 * * * *"}
    response = client.post("/api/review-schedules", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["batchSize"] == 50


def test_create_review_schedule_unknown_review_type_returns_404(client: TestClient):
    response = client.post(
        "/api/review-schedules",
        json={"name": "x", "reviewTypeId": str(uuid4()), "cron": "0 * * * *"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Review type not found"


def test_create_review_schedule_invalid_cron_returns_422(client: TestClient):
    _seed_stores()
    response = client.post(
        "/api/review-schedules",
        json={"name": "x", "reviewTypeId": REVIEW_TYPE_ID, "cron": "not-a-cron"},
    )

    assert response.status_code == 422


def test_update_review_schedule_fields(client: TestClient, monkeypatch):
    created = _create_review_schedule(client, monkeypatch)

    response = client.put(
        f"/api/review-schedules/{created['id']}",
        json={
            "name": "每十分钟复核",
            "reviewTypeId": REVIEW_TYPE_ID,
            "cron": "*/10 * * * *",
            "enabled": False,
            "batchSize": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "每十分钟复核"
    assert payload["cron"] == "*/10 * * * *"
    assert payload["enabled"] is False
    assert payload["batchSize"] == 5
    assert payload["updatedAt"] >= created["updatedAt"]


def test_update_review_schedule_unknown_id_returns_404(client: TestClient):
    _seed_stores()
    response = client.put(
        f"/api/review-schedules/{uuid4()}",
        json={"name": "x", "reviewTypeId": REVIEW_TYPE_ID, "cron": "0 * * * *"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Review schedule not found"


def test_update_review_schedule_invalid_cron_returns_422(client: TestClient, monkeypatch):
    created = _create_review_schedule(client, monkeypatch)

    response = client.put(
        f"/api/review-schedules/{created['id']}",
        json={"name": "x", "reviewTypeId": REVIEW_TYPE_ID, "cron": "61 * * * *"},
    )

    assert response.status_code == 422


def test_delete_review_schedule_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(review_schedules_router, "delete_review_schedule_from_db", lambda schedule_id: None)
    created = _create_review_schedule(client, monkeypatch)

    response = client.delete(f"/api/review-schedules/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/review-schedules").json() == []


def test_delete_review_schedule_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/review-schedules/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review schedule not found"


# ---------------- 手动 run 端到端 ----------------


def _mock_execution_env(monkeypatch, events: list, updated: list) -> None:
    """把执行链路的外部依赖（事件查询/快照读取/大模型/落库/回写）替换为假实现。"""
    monkeypatch.setattr(review_schedules_service, "_query_pending_events", lambda schedule: list(events))
    monkeypatch.setattr(
        review_schedules_service,
        "_read_snapshot_bytes",
        lambda snapshot_url: FAKE_IMAGE_BYTES if snapshot_url == SNAPSHOT_URL else None,
    )
    monkeypatch.setattr(review_schedules_service, "persist_review_task", lambda record: None)
    monkeypatch.setattr(review_schedules_service, "persist_review_schedule", lambda record: None)
    monkeypatch.setattr(
        review_schedules_service.llm_client,
        "judge_event",
        lambda **kwargs: ("有效", "检测到目标"),
    )

    def _fake_update(event_id, verdict):
        updated.append((event_id, verdict))

    monkeypatch.setattr(review_schedules_service, "update_deployment_event_review_status", _fake_update)


def test_manual_run_reviews_events_and_writes_back(client: TestClient, monkeypatch):
    created = _create_review_schedule(client, monkeypatch)
    event_id = str(uuid4())
    updated: list = []
    _mock_execution_env(monkeypatch, [(event_id, SNAPSHOT_URL)], updated)

    response = client.post(f"/api/review-schedules/{created['id']}/run")

    assert response.status_code == 200
    assert response.json() == {"started": created["id"]}

    last_result = _wait_last_result(created["id"])
    assert last_result == "处理 1 条：有效 1 / 无效 0 / 失败 0 / 跳过 0"
    # 事件 review_status 已回写
    assert updated == [(event_id, "有效")]
    # 复核任务留痕
    tasks = client.get("/api/review-tasks").json()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["reviewTypeId"] == REVIEW_TYPE_ID
    assert task["reviewTypeCode"] == "person_fall"
    assert task["llmConfigId"] == LLM_CONFIG_ID
    assert task["imageUrl"] == SNAPSHOT_URL
    assert task["status"] == "已完成"
    assert task["verdict"] == "有效"
    assert task["reason"] == "检测到目标"
    # lastRunAt 已更新
    schedule = client.get("/api/review-schedules").json()[0]
    assert schedule["lastRunAt"] is not None
    assert schedule["lastResult"] == last_result


def test_run_skips_missing_snapshot_and_counts_it(client: TestClient, monkeypatch):
    created = _create_review_schedule(client, monkeypatch)
    updated: list = []
    events = [(str(uuid4()), SNAPSHOT_URL), (str(uuid4()), "/api/assets/snapshots/missing.jpg")]
    _mock_execution_env(monkeypatch, events, updated)

    review_schedules_service.execute_review_schedule(created["id"])

    record = state.review_schedules_store[created["id"]]
    assert record["last_result"] == "处理 2 条：有效 1 / 无效 0 / 失败 0 / 跳过 1"
    assert len(updated) == 1


def test_run_marks_failure_when_llm_config_missing(client: TestClient, monkeypatch):
    created = _create_review_schedule(client, monkeypatch)
    state.llm_configs_store.clear()  # 复核类型关联的大模型配置不存在
    updated: list = []
    _mock_execution_env(monkeypatch, [(str(uuid4()), SNAPSHOT_URL)], updated)

    review_schedules_service.execute_review_schedule(created["id"])

    record = state.review_schedules_store[created["id"]]
    assert record["last_result"] == "处理 1 条：有效 0 / 无效 0 / 失败 1 / 跳过 0"
    # 判定失败不回写 review_status（下次触发重试）
    assert updated == []
    task = client.get("/api/review-tasks").json()[0]
    assert task["status"] == "失败"
    assert task["reason"] == "无大模型配置"


def test_run_unknown_schedule_returns_404(client: TestClient):
    response = client.post(f"/api/review-schedules/{uuid4()}/run")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review schedule not found"


# ---------------- 快照读取与 cron 工具 ----------------


def test_read_snapshot_bytes_roundtrip_and_missing():
    snapshot_dir = get_settings().snapshot_storage_dir
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / "pytest-review-schedule.jpg"
    path.write_bytes(FAKE_IMAGE_BYTES)
    try:
        assert review_schedules_service._read_snapshot_bytes(f"/api/assets/snapshots/{path.name}") == FAKE_IMAGE_BYTES
    finally:
        path.unlink(missing_ok=True)
    assert review_schedules_service._read_snapshot_bytes("/api/assets/snapshots/not-exists.jpg") is None
    assert review_schedules_service._read_snapshot_bytes("") is None


def test_validate_cron_accepts_valid_and_rejects_invalid():
    review_schedules_service.validate_cron("*/5 * * * *")
    review_schedules_service.validate_cron("0 3 * * 1-5")
    try:
        review_schedules_service.validate_cron("definitely not cron")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid cron")


def test_schedule_due_uses_last_run_or_created_at():
    old = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    schedule = {"cron": "0 * * * *", "created_at": old, "last_run_at": None}
    assert review_schedules_service._schedule_due(schedule) is True
    # 最近一次运行距今不足一个周期时未到点
    schedule["last_run_at"] = datetime.now(timezone.utc)
    assert review_schedules_service._schedule_due(schedule) is False
