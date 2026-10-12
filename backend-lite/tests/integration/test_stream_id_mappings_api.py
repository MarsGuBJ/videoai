"""流ID映射代理接口的集成测试。"""

import pytest
import requests
from fastapi.testclient import TestClient

from app.core.config import get_settings

IMPORT_BODY = {
    "rows": [
        {"streamId": "stream-1", "cameraHost": "192.168.1.11"},
        {"streamId": "stream-2", "cameraHost": "192.168.1.12"},
    ],
    "cvr": {"host": "192.168.1.20", "port": 8000, "username": "admin", "password": "s3cret"},
}

LIST_PAYLOAD = {
    "data": [
        {
            "cameraHost": "192.168.1.11",
            "streamId": "stream-1",
            "cvrHost": "192.168.1.20",
            "cvrPort": 8000,
            "username": "admin",
        }
    ]
}


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
    """列表正常透传，字段原样返回。"""
    captured: list = []
    _fake_mcp_get(monkeypatch, LIST_PAYLOAD, captured)

    response = client.get("/api/stream-id-mappings")

    assert response.status_code == 200
    assert response.json() == [
        {
            "cameraHost": "192.168.1.11",
            "streamId": "stream-1",
            "cvrHost": "192.168.1.20",
            "cvrPort": 8000,
            "username": "admin",
        }
    ]
    assert captured[0]["url"] == f"{get_settings().mcp_server_base_url}/stream-id-mappings"
    assert captured[0]["timeout"] == 30


def test_list_malformed_data_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP data 非列表时返回 502。"""
    _fake_mcp_get(monkeypatch, {"data": {"unexpected": True}})

    response = client.get("/api/stream-id-mappings")

    assert response.status_code == 502


def test_import_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """导入请求体原样透传给 MCP，返回 imported 数量与 skipped 明细；逐行校验耗时，超时放宽。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {"/stream-id-mappings/import": {"data": {"imported": 2, "skipped": []}}}, captured)

    response = client.post("/api/stream-id-mappings/import", json=IMPORT_BODY)

    assert response.status_code == 200
    assert response.json() == {"imported": 2, "skipped": []}
    call = captured[0]
    assert call["url"] == f"{get_settings().mcp_server_base_url}/stream-id-mappings/import"
    assert call["timeout"] == 120
    assert call["json"] == IMPORT_BODY


def test_import_passes_through_skipped(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 校验跳过明细（row + reason）原样透传。"""
    _fake_mcp_post(
        monkeypatch,
        {
            "/stream-id-mappings/import": {
                "data": {
                    "imported": 1,
                    "skipped": [
                        {
                            "row": {"streamId": "stream-2", "cameraHost": "192.168.1.12"},
                            "reason": "CVR 上查询不到该流ID",
                        }
                    ],
                }
            }
        },
    )

    response = client.post("/api/stream-id-mappings/import", json=IMPORT_BODY)

    assert response.status_code == 200
    assert response.json() == {
        "imported": 1,
        "skipped": [{"row": {"streamId": "stream-2", "cameraHost": "192.168.1.12"}, "reason": "CVR 上查询不到该流ID"}],
    }


def test_import_malformed_data_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP data 非对象时返回 502。"""
    _fake_mcp_post(monkeypatch, {"/stream-id-mappings/import": {"data": "oops"}})

    response = client.post("/api/stream-id-mappings/import", json=IMPORT_BODY)

    assert response.status_code == 502


def test_empty_rows_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """rows 为空列表时 422，不调用 MCP。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {}, captured)

    response = client.post("/api/stream-id-mappings/import", json={**IMPORT_BODY, "rows": []})

    assert response.status_code == 422
    assert captured == []


@pytest.mark.parametrize("field", ["host", "username", "password"])
def test_blank_cvr_required_text_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch, field: str):
    """CVR 主机 / 账号 / 密码只填空白时 422，不调用 MCP。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {}, captured)

    cvr = {**IMPORT_BODY["cvr"], field: "   "}
    response = client.post("/api/stream-id-mappings/import", json={**IMPORT_BODY, "cvr": cvr})

    assert response.status_code == 422
    assert captured == []


def test_blank_row_text_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """导入行的 streamId / cameraHost 只填空白时 422，不调用 MCP。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {}, captured)

    body = {**IMPORT_BODY, "rows": [{"streamId": "  ", "cameraHost": "192.168.1.11"}]}
    response = client.post("/api/stream-id-mappings/import", json=body)

    assert response.status_code == 422
    assert captured == []


def test_mcp_unavailable_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 不可达时返回 502。"""
    _fake_mcp_get(monkeypatch, requests.ConnectionError("refused"))

    response = client.get("/api/stream-id-mappings")

    assert response.status_code == 502


def test_mcp_param_error_returns_400(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 报参数类错误时透传为 400。"""
    _fake_mcp_post(
        monkeypatch,
        {"/stream-id-mappings/import": {"error": {"type": "InvalidParams", "message": "streamId 不能为空"}}},
    )

    response = client.post("/api/stream-id-mappings/import", json=IMPORT_BODY)

    assert response.status_code == 400
    assert "streamId 不能为空" in response.json()["detail"]


def test_mcp_not_configured_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP_SERVER_BASE_URL 未配置时返回 500。"""
    monkeypatch.setattr(get_settings(), "mcp_server_base_url", "")

    response = client.get("/api/stream-id-mappings")

    assert response.status_code == 500
