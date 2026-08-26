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
        json={"name": "北门布控", "cameraIds": ["cam-1"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "北门布控"
    assert payload["pipeline"] == "人脸识别流程"
    assert payload["enabled"] is True
    assert payload["taskStatus"] == "running"
    assert payload["cameraIds"] == ["cam-1"]
    assert payload["recognitionPerMinute"] == 60
    assert payload["id"]
    assert payload["createdAt"]
    assert payload["updatedAt"]
    assert len(persisted) == 1
    assert len(synced) == 1


def test_get_deployment_task_unknown_id_returns_404(client: TestClient):
    response = client.get(f"/api/deployment-tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Deployment task not found"


def test_unknown_api_path_returns_404(client: TestClient):
    response = client.get("/api/no-such-route")

    assert response.status_code == 404
