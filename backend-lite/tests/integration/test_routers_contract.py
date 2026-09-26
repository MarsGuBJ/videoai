"""主路径路由契约测试：TestClient 直连，外部依赖（DB、worker）按手册 3.3.1 在使用处 mock。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.deployment_tasks as deployment_tasks_router


def test_health_returns_ok(client: TestClient):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_faces_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/faces")

    assert response.status_code == 200
    assert response.json() == []


def test_create_face_missing_form_fields_returns_422(client: TestClient):
    response = client.post("/api/faces")

    assert response.status_code == 422


def test_list_deployment_tasks_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/deployment-tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_deployment_task_missing_name_returns_422(client: TestClient):
    response = client.post("/api/deployment-tasks", json={})

    assert response.status_code == 422


def test_create_deployment_task_valid_payload_returns_camel_case_contract(client: TestClient, monkeypatch):
    persisted = []
    synced = []
    # mock 边界：DB 落库与 worker 流同步，在使用处（路由模块命名空间）替换
    monkeypatch.setattr(deployment_tasks_router, "persist_deployment_task", persisted.append)
    monkeypatch.setattr(deployment_tasks_router, "sync_worker_streams_for_task", synced.append)

    response = client.post(
        "/api/deployment-tasks",
        json={"name": "北门布控", "cameraIds": ["cam-1"], "algorithmCode": "algo-gather-v1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "北门布控"
    assert payload["pipeline"] == "人脸识别流程"
    assert payload["enabled"] is True
    assert payload["taskStatus"] == "running"
    assert payload["cameraIds"] == ["cam-1"]
    assert payload["recognitionPerMinute"] == 60
    assert payload["algorithmCode"] == "algo-gather-v1"
    assert payload["id"]
    assert payload["createdAt"]
    assert payload["updatedAt"]
    assert len(persisted) == 1
    assert len(synced) == 1


def test_update_deployment_task_passes_through_algorithm_code(client: TestClient, monkeypatch):
    persisted = []
    synced = []
    # mock 边界：DB 落库与 worker 流同步，在使用处（路由模块命名空间）替换
    monkeypatch.setattr(deployment_tasks_router, "persist_deployment_task", persisted.append)
    monkeypatch.setattr(deployment_tasks_router, "sync_worker_streams_for_task", synced.append)

    created = client.post("/api/deployment-tasks", json={"name": "东门布控", "cameraIds": []}).json()
    assert created["algorithmCode"] is None

    response = client.patch(
        f"/api/deployment-tasks/{created['id']}",
        json={"algorithmCode": "algo-gather-v1"},
    )

    assert response.status_code == 200
    assert response.json()["algorithmCode"] == "algo-gather-v1"
    assert persisted[-1].algorithmCode == "algo-gather-v1"

    # 显式置空可清除编码
    response = client.patch(f"/api/deployment-tasks/{created['id']}", json={"algorithmCode": None})
    assert response.status_code == 200
    assert response.json()["algorithmCode"] is None


def test_deployment_task_strategy_fields_round_trip(client: TestClient, monkeypatch):
    persisted = []
    synced = []
    # mock 边界：DB 落库与 worker 流同步，在使用处（路由模块命名空间）替换
    monkeypatch.setattr(deployment_tasks_router, "persist_deployment_task", persisted.append)
    monkeypatch.setattr(deployment_tasks_router, "sync_worker_streams_for_task", synced.append)

    response = client.post(
        "/api/deployment-tasks",
        json={
            "name": "西门布控",
            "cameraIds": ["cam-1"],
            "similarity": 80,
            "effectiveStart": "2026-10-01",
            "effectiveEnd": "2026-12-31",
            "cycleStart": "08:00",
            "cycleEnd": "20:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["similarity"] == 80
    assert payload["effectiveStart"] == "2026-10-01"
    assert payload["effectiveEnd"] == "2026-12-31"
    assert payload["cycleStart"] == "08:00"
    assert payload["cycleEnd"] == "20:00"

    # 缺省时给默认值
    created = client.post("/api/deployment-tasks", json={"name": "南门布控", "cameraIds": []}).json()
    assert created["similarity"] == 50
    assert created["effectiveStart"] is None
    assert created["cycleStart"] is None

    # 部分更新与显式置空
    response = client.patch(f"/api/deployment-tasks/{payload['id']}", json={"similarity": 65, "cycleEnd": "22:30"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["similarity"] == 65
    assert updated["cycleEnd"] == "22:30"
    assert updated["effectiveStart"] == "2026-10-01"
    response = client.patch(f"/api/deployment-tasks/{payload['id']}", json={"effectiveStart": None})
    assert response.status_code == 200
    assert response.json()["effectiveStart"] is None

    # 越界相似度按 422 拦截
    response = client.post("/api/deployment-tasks", json={"name": "非法", "cameraIds": [], "similarity": 120})
    assert response.status_code == 422


def test_get_deployment_task_unknown_id_returns_404(client: TestClient):
    response = client.get(f"/api/deployment-tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Deployment task not found"


def test_unknown_api_path_returns_404(client: TestClient):
    response = client.get("/api/no-such-route")

    assert response.status_code == 404
