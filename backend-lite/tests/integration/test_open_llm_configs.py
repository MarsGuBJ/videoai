"""对外开放接口契约测试：/api/open/llm-configs/{model_config_id}。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.llm_configs as llm_configs_router

CREATE_PAYLOAD = {
    "name": "通义千问",
    "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
    "model": "qwen-vl-max",
    "apiKey": "sk-secret-key",
    "deployType": "cloud",
}


def _create_config(client: TestClient, monkeypatch) -> dict:
    monkeypatch.setattr(llm_configs_router, "persist_llm_config", lambda record: None)
    response = client.post("/api/llm-configs", json=CREATE_PAYLOAD)
    assert response.status_code == 200
    return response.json()


def test_open_get_llm_config_returns_config_with_plain_api_key(client: TestClient, monkeypatch):
    created = _create_config(client, monkeypatch)

    response = client.get(f"/api/open/llm-configs/{created['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created["id"]
    assert payload["name"] == "通义千问"
    assert payload["baseUrl"] == CREATE_PAYLOAD["baseUrl"]
    assert payload["model"] == "qwen-vl-max"
    assert payload["apiKey"] == "sk-secret-key"
    assert payload["deployType"] == "cloud"


def test_open_get_llm_config_unknown_id_returns_404(client: TestClient):
    response = client.get(f"/api/open/llm-configs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "LLM config not found"
