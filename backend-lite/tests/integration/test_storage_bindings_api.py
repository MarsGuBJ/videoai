"""录像存储绑定代理接口的集成测试。"""

import pytest
import requests
from fastapi.testclient import TestClient

from app.core.config import get_settings

BIND_BODY = {"cameraIds": ["cam-1", "cam-2"], "storageHost": "192.168.1.10", "username": "admin", "password": "s3cret"}

LIST_PAYLOAD = {"data": [{"cameraId": "cam-1", "host": "192.168.1.10", "username": "admin"}]}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self.payload


def _fake_mcp_get(monkeypatch: pytest.MonkeyPatch, response, captured: list | None = None):
    """替换 requests.get；response 为 dict（200）或 requests 异常实例。"""

    def fake_get(url, timeout):
        if captured is not None:
            captured.append({"url": url, "timeout": timeout})
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)

    monkeypatch.setattr(requests, "get", fake_get)


def _fake_mcp_post(monkeypatch: pytest.MonkeyPatch, responses: dict[str, object], captured: list | None = None):
    """按 URL 后缀分发 MCP 响应；responses 值为 dict（200）或 requests 异常实例。"""

    def fake_post(url, json, timeout):
        if captured is not None:
            captured.append({"url": url, "json": json, "timeout": timeout})
        for suffix, response in responses.items():
            if url.endswith(suffix):
                if isinstance(response, Exception):
                    raise response
                return FakeResponse(response)
        raise AssertionError(f"unexpected MCP url: {url}")

    monkeypatch.setattr(requests, "post", fake_post)


def test_list_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """列表正常透传，且 MCP 的 host 字段映射为 storageHost。"""
    captured: list = []
    _fake_mcp_get(monkeypatch, LIST_PAYLOAD, captured)

    response = client.get("/api/storage-bindings")

    assert response.status_code == 200
    body = response.json()
    assert body == [{"cameraId": "cam-1", "storageHost": "192.168.1.10", "username": "admin"}]
    assert captured[0]["url"] == f"{get_settings().mcp_server_base_url}/storage-bindings"
    assert captured[0]["timeout"] == 30


def test_list_malformed_data_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP data 非列表时返回 502。"""
    _fake_mcp_get(monkeypatch, {"data": {"unexpected": True}})

    response = client.get("/api/storage-bindings")

    assert response.status_code == 502


def test_bind_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """绑定请求按 items 形状转发给 MCP，返回 bound 数量与 skipped 明细；校验耗时，超时放宽。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {"/storage-bindings/bind": {"data": {"bound": 2, "skipped": []}}}, captured)

    response = client.post("/api/storage-bindings/bind", json=BIND_BODY)

    assert response.status_code == 200
    assert response.json() == {"bound": 2, "skipped": []}
    call = captured[0]
    assert call["url"].endswith("/storage-bindings/bind")
    assert call["timeout"] == 120
    assert call["json"] == {
        "items": [
            {"cameraId": "cam-1", "host": "192.168.1.10", "username": "admin", "password": "s3cret"},
            {"cameraId": "cam-2", "host": "192.168.1.10", "username": "admin", "password": "s3cret"},
        ]
    }


def test_bind_passes_through_skipped(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 校验跳过明细原样透传（storageHost 维度在 MCP 侧处理，这里只映射字段）。"""
    _fake_mcp_post(
        monkeypatch,
        {
            "/storage-bindings/bind": {
                "data": {"bound": 1, "skipped": [{"cameraId": "cam-2", "reason": "存储设备上查询不到该摄像头的录像"}]}
            }
        },
    )

    response = client.post("/api/storage-bindings/bind", json=BIND_BODY)

    assert response.status_code == 200
    assert response.json() == {
        "bound": 1,
        "skipped": [{"cameraId": "cam-2", "reason": "存储设备上查询不到该摄像头的录像"}],
    }


def test_unbind_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """解绑请求按 cameraIds 形状转发，返回 unbound 数量。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {"/storage-bindings/unbind": {"data": {"unbound": 1}}}, captured)

    response = client.post("/api/storage-bindings/unbind", json={"cameraIds": ["cam-1"]})

    assert response.status_code == 200
    assert response.json() == {"unbound": 1}
    assert captured[0]["json"] == {"cameraIds": ["cam-1"]}


@pytest.mark.parametrize("endpoint", ["/api/storage-bindings/bind", "/api/storage-bindings/unbind"])
def test_empty_camera_ids_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch, endpoint: str):
    """cameraIds 为空列表时 422，不调用 MCP。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {}, captured)

    body = {**BIND_BODY, "cameraIds": []} if endpoint.endswith("bind") else {"cameraIds": []}
    response = client.post(endpoint, json=body)

    assert response.status_code == 422
    assert captured == []


@pytest.mark.parametrize("field", ["storageHost", "username", "password"])
def test_blank_required_text_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch, field: str):
    """主机 / 账号 / 密码只填空白时 422，不调用 MCP。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {}, captured)

    response = client.post("/api/storage-bindings/bind", json={**BIND_BODY, field: "   "})

    assert response.status_code == 422
    assert captured == []


def test_mcp_unavailable_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 不可达时返回 502。"""
    _fake_mcp_get(monkeypatch, requests.ConnectionError("refused"))

    response = client.get("/api/storage-bindings")

    assert response.status_code == 502


def test_mcp_param_error_returns_400(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 报参数类错误时透传为 400。"""
    _fake_mcp_post(
        monkeypatch,
        {"/storage-bindings/bind": {"error": {"type": "InvalidParams", "message": "cameraId 不存在"}}},
    )

    response = client.post("/api/storage-bindings/bind", json=BIND_BODY)

    assert response.status_code == 400
    assert "cameraId 不存在" in response.json()["detail"]


def test_mcp_not_configured_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP_SERVER_BASE_URL 未配置时返回 500。"""
    monkeypatch.setattr(get_settings(), "mcp_server_base_url", "")

    response = client.get("/api/storage-bindings")

    assert response.status_code == 500


RESOLVED_PAYLOAD = {
    "data": [
        {"cameraId": "cam-1", "host": "10.10.7.252", "bound": False},
        {"cameraId": "cam-2", "host": "192.168.1.10", "bound": True},
    ]
}


def test_resolved_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """resolved 列表正常透传，host 映射为 storageHost，bound 标记原样保留。"""
    captured: list = []
    _fake_mcp_get(monkeypatch, RESOLVED_PAYLOAD, captured)

    response = client.get("/api/storage-bindings/resolved")

    assert response.status_code == 200
    assert response.json() == [
        {"cameraId": "cam-1", "storageHost": "10.10.7.252", "bound": False},
        {"cameraId": "cam-2", "storageHost": "192.168.1.10", "bound": True},
    ]
    assert captured[0]["url"] == f"{get_settings().mcp_server_base_url}/storage-bindings/resolved"


def test_resolved_malformed_data_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """resolved 接口 MCP data 非列表时返回 502。"""
    _fake_mcp_get(monkeypatch, {"data": "oops"})

    response = client.get("/api/storage-bindings/resolved")

    assert response.status_code == 502
