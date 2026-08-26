"""大模型配置路由契约测试：TestClient 直连，DB 落库与连接检测在路由模块命名空间 mock。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.llm_configs as llm_configs_router

CREATE_PAYLOAD = {
    "name": "通义千问",
    "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
    "apiKey": "sk-secret-key",
    "deployType": "cloud",
}


def _create_config(client: TestClient, monkeypatch, **overrides) -> dict:
    monkeypatch.setattr(llm_configs_router, "persist_llm_config", lambda record: None)
    payload = {**CREATE_PAYLOAD, **overrides}
    response = client.post("/api/llm-configs", json=payload)
    assert response.status_code == 200
    return response.json()


def test_list_llm_configs_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/llm-configs")

    assert response.status_code == 200
    assert response.json() == []


def test_create_llm_config_missing_required_fields_returns_422(client: TestClient):
    response = client.post("/api/llm-configs", json={})

    assert response.status_code == 422


def test_create_then_list_returns_masked_api_key_and_camel_case(client: TestClient, monkeypatch):
    created = _create_config(client, monkeypatch)

    assert created["name"] == "通义千问"
    # baseUrl 尾斜杠原样保存（仅检测时裁剪）
    assert created["baseUrl"] == CREATE_PAYLOAD["baseUrl"]
    assert created["apiKey"] == "sk-***"
    assert created["apiKeyConfigured"] is True
    assert created["deployType"] == "cloud"
    assert created["timeout"] == 30
    assert created["temperature"] == 0.7
    assert created["maxTokens"] == 2048
    assert created["fps"] == 1
    assert created["id"]
    assert created["createdAt"]
    assert created["updatedAt"]

    listed = client.get("/api/llm-configs").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]
    assert listed[0]["apiKey"] == "sk-***"
    assert listed[0]["apiKeyConfigured"] is True


def test_create_llm_config_without_api_key_marks_unconfigured(client: TestClient, monkeypatch):
    created = _create_config(client, monkeypatch, apiKey="")

    assert created["apiKey"] == ""
    assert created["apiKeyConfigured"] is False


def test_update_llm_config_empty_api_key_keeps_original(client: TestClient, monkeypatch):
    created = _create_config(client, monkeypatch)

    response = client.put(
        f"/api/llm-configs/{created['id']}",
        json={"name": "本地 vLLM", "apiKey": "", "timeout": 60, "deployType": "local"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "本地 vLLM"
    assert payload["timeout"] == 60
    assert payload["deployType"] == "local"
    # apiKey 传空保留原值：掩码与 configured 标记不变
    assert payload["apiKey"] == "sk-***"
    assert payload["apiKeyConfigured"] is True


def test_update_llm_config_new_api_key_replaces_original(client: TestClient, monkeypatch):
    created = _create_config(client, monkeypatch)

    response = client.put(f"/api/llm-configs/{created['id']}", json={"apiKey": "new-token-123"})

    assert response.status_code == 200
    assert response.json()["apiKey"] == "new***"


def test_update_llm_config_unknown_id_returns_404(client: TestClient):
    response = client.put(f"/api/llm-configs/{uuid4()}", json={"name": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "LLM config not found"


def test_delete_llm_config_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(llm_configs_router, "delete_llm_config_from_db", lambda config_id: None)
    created = _create_config(client, monkeypatch)

    response = client.delete(f"/api/llm-configs/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/llm-configs").json() == []


def test_delete_llm_config_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/llm-configs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "LLM config not found"


def test_llm_config_test_endpoint_returns_fixed_result(client: TestClient, monkeypatch):
    created = _create_config(client, monkeypatch)
    fixed = {
        "ok": True,
        "latencyMs": 123,
        "statusCode": 200,
        "error": None,
        "checkedAt": "2026-08-25T10:00:00Z",
    }
    monkeypatch.setattr(llm_configs_router, "test_llm_connection", lambda cfg: fixed)

    response = client.post(f"/api/llm-configs/{created['id']}/test")

    assert response.status_code == 200
    assert response.json() == fixed


def test_llm_config_test_endpoint_unknown_id_returns_404(client: TestClient):
    response = client.post(f"/api/llm-configs/{uuid4()}/test")

    assert response.status_code == 404
    assert response.json()["detail"] == "LLM config not found"
