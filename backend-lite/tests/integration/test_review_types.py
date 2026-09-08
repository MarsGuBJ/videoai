"""复核类型路由契约测试：TestClient 直连，DB 落库在路由模块命名空间 mock。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.review_types as review_types_router

CREATE_PAYLOAD = {
    "name": "人员跌倒",
    "code": "person_fall",
    "prompt": "请判断画面中是否有人跌倒",
    "injectEvent": "event_info",
    "remark": "一期上线",
}


def _create_review_type(client: TestClient, monkeypatch, **overrides) -> dict:
    monkeypatch.setattr(review_types_router, "persist_review_type", lambda record: None)
    payload = {**CREATE_PAYLOAD, **overrides}
    response = client.post("/api/review-types", json=payload)
    assert response.status_code == 200
    return response.json()


def test_list_review_types_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/review-types")

    assert response.status_code == 200
    assert response.json() == []


def test_create_review_type_missing_required_fields_returns_422(client: TestClient):
    response = client.post("/api/review-types", json={})

    assert response.status_code == 422


def test_create_then_list_contains_created_record(client: TestClient, monkeypatch):
    created = _create_review_type(client, monkeypatch)

    assert created["name"] == "人员跌倒"
    assert created["code"] == "person_fall"
    assert created["prompt"] == "请判断画面中是否有人跌倒"
    assert created["injectEvent"] == "event_info"
    assert created["remark"] == "一期上线"
    assert created["id"]
    assert created["createdAt"]
    assert created["updatedAt"]

    listed = client.get("/api/review-types").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


def test_create_review_type_optional_fields_default_empty(client: TestClient, monkeypatch):
    monkeypatch.setattr(review_types_router, "persist_review_type", lambda record: None)
    # 缺省 injectEvent/remark 字段落为默认空串
    payload = {"name": "烟雾检测", "code": "smoke", "prompt": "是否有烟雾"}
    response = client.post("/api/review-types", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["injectEvent"] == ""
    assert body["remark"] == ""


def test_update_review_type_partial_fields(client: TestClient, monkeypatch):
    created = _create_review_type(client, monkeypatch)

    response = client.put(
        f"/api/review-types/{created['id']}",
        json={"name": "人员摔倒", "remark": "二期调整"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "人员摔倒"
    assert payload["remark"] == "二期调整"
    # 未传字段保留原值
    assert payload["code"] == "person_fall"
    assert payload["prompt"] == "请判断画面中是否有人跌倒"
    assert payload["injectEvent"] == "event_info"
    assert payload["updatedAt"] >= created["updatedAt"]


def test_update_review_type_unknown_id_returns_404(client: TestClient):
    response = client.put(f"/api/review-types/{uuid4()}", json={"name": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Review type not found"


def test_review_type_llm_config_id_create_update_clear(client: TestClient, monkeypatch):
    llm_id = str(uuid4())
    created = _create_review_type(client, monkeypatch, llmConfigId=llm_id)
    assert created["llmConfigId"] == llm_id

    # 未传 llmConfigId 时保留原值
    kept = client.put(f"/api/review-types/{created['id']}", json={"remark": "保留"})
    assert kept.json()["llmConfigId"] == llm_id

    # 传空字符串清除关联
    cleared = client.put(f"/api/review-types/{created['id']}", json={"llmConfigId": ""})
    assert cleared.json()["llmConfigId"] is None


def test_delete_review_type_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(review_types_router, "delete_review_type_from_db", lambda type_id: None)
    created = _create_review_type(client, monkeypatch)

    response = client.delete(f"/api/review-types/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/review-types").json() == []


def test_delete_review_type_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/review-types/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review type not found"
