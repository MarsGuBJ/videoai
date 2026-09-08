"""复核任务路由与判定流程契约测试：TestClient 直连，DB 落库与后台判定在测试中 mock。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.review_tasks as review_tasks_router
import app.services.review_tasks as review_tasks_service
from app import state

FAKE_IMAGE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
FAKE_IMAGE_URL = "/api/assets/review-images/fake.jpg"

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


def _seed_stores() -> None:
    state.review_types_store[REVIEW_TYPE_ID] = dict(REVIEW_TYPE_RECORD)
    state.llm_configs_store[LLM_CONFIG_ID] = dict(LLM_CONFIG_RECORD)


def _create_review_task(client: TestClient, monkeypatch, **overrides) -> dict:
    """经 API 创建复核任务；图片落盘与后台判定线程替换为假实现，避免外部依赖。"""
    _seed_stores()
    monkeypatch.setattr(review_tasks_router, "persist_review_task", lambda record: None)
    monkeypatch.setattr(review_tasks_router, "save_review_image", _fake_save_review_image)
    monkeypatch.setattr(review_tasks_router, "run_review_task_judgment", lambda task_id, image_bytes: None)
    data = {"reviewTypeId": REVIEW_TYPE_ID, "llmConfigId": LLM_CONFIG_ID, **overrides}
    response = client.post(
        "/api/review-tasks",
        data=data,
        files={"image": ("test.jpg", FAKE_IMAGE_BYTES, "image/jpeg")},
    )
    assert response.status_code == 200
    return response.json()


async def _fake_save_review_image(image) -> str:
    return FAKE_IMAGE_URL


def test_list_review_tasks_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/review-tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_then_list_contains_created_record(client: TestClient, monkeypatch):
    created = _create_review_task(client, monkeypatch)

    assert created["id"]
    assert created["reviewTypeId"] == REVIEW_TYPE_ID
    # 快照字段取自创建时的复核类型 / 大模型配置
    assert created["reviewTypeName"] == "人员跌倒"
    assert created["reviewTypeCode"] == "person_fall"
    assert created["llmConfigId"] == LLM_CONFIG_ID
    assert created["llmConfigName"] == "本地 Qwen-VL"
    assert created["imageUrl"] == FAKE_IMAGE_URL
    # 判定在后台线程执行，创建响应时仍为进行中
    assert created["status"] == "进行中"
    assert created["verdict"] == ""
    assert created["reason"] == ""
    assert created["createdAt"]
    assert created["updatedAt"]

    listed = client.get("/api/review-tasks").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


def test_create_review_task_unknown_review_type_returns_404(client: TestClient, monkeypatch):
    _seed_stores()
    response = client.post(
        "/api/review-tasks",
        data={"reviewTypeId": str(uuid4()), "llmConfigId": LLM_CONFIG_ID},
        files={"image": ("test.jpg", FAKE_IMAGE_BYTES, "image/jpeg")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Review type not found"


def test_create_review_task_unknown_llm_config_returns_404(client: TestClient, monkeypatch):
    _seed_stores()
    response = client.post(
        "/api/review-tasks",
        data={"reviewTypeId": REVIEW_TYPE_ID, "llmConfigId": str(uuid4())},
        files={"image": ("test.jpg", FAKE_IMAGE_BYTES, "image/jpeg")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "LLM config not found"


def test_judgment_success_marks_task_completed(client: TestClient, monkeypatch):
    created = _create_review_task(client, monkeypatch)
    monkeypatch.setattr(
        review_tasks_service.llm_client,
        "judge_event",
        lambda **kwargs: ("有效", "检测到目标"),
    )
    monkeypatch.setattr(review_tasks_service, "persist_review_task", lambda record: None)

    review_tasks_service.run_review_task_judgment(created["id"], FAKE_IMAGE_BYTES)

    fetched = client.get(f"/api/review-tasks/{created['id']}").json()
    assert fetched["status"] == "已完成"
    assert fetched["verdict"] == "有效"
    assert fetched["reason"] == "检测到目标"
    assert fetched["updatedAt"] >= created["updatedAt"]


def test_judgment_failure_marks_task_failed(client: TestClient, monkeypatch):
    created = _create_review_task(client, monkeypatch)

    def _raise(**kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(review_tasks_service.llm_client, "judge_event", _raise)
    monkeypatch.setattr(review_tasks_service, "persist_review_task", lambda record: None)

    review_tasks_service.run_review_task_judgment(created["id"], FAKE_IMAGE_BYTES)

    fetched = client.get(f"/api/review-tasks/{created['id']}").json()
    assert fetched["status"] == "失败"
    assert fetched["reason"]
    assert "connection refused" in fetched["reason"]


def test_get_review_task_unknown_id_returns_404(client: TestClient):
    response = client.get(f"/api/review-tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review task not found"


def test_delete_review_task_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(review_tasks_router, "delete_review_task_from_db", lambda task_id: None)
    created = _create_review_task(client, monkeypatch)

    response = client.delete(f"/api/review-tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/review-tasks").json() == []


def test_delete_review_task_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/review-tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review task not found"
