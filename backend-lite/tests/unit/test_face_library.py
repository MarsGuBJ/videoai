"""人脸照片库代理（/api/face-library/page）测试。

代理转发外部人脸照片模块 ``/face/es/label/facePage``：成功时透传分页数据，
业务码非成功或连接异常时返回 502。
"""

from types import SimpleNamespace

import pytest
import requests
from fastapi.testclient import TestClient

from app.services import face_library

FACE_PHOTO_BASE = "http://113.249.91.53:8421"

PAGE_DATA = {
    "total": 1,
    "current": 1,
    "size": 12,
    "records": [
        {
            "id": "1812345678901234567",
            "name": "zhangsan.jpg",
            "url": "http://minio.example.com/face-lib/zhangsan.jpg",
            "createTime": "2024-06-15 10:30:00",
            "description": [{"keyName": "personName", "val": "张三"}],
        }
    ],
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self.payload


def _stub_settings():
    return SimpleNamespace(face_photo_api_base_url=FACE_PHOTO_BASE)


def test_face_page_success(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """成功时透传分页数据，关键字映射到 query.val。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"code": "0", "msg": "success", "data": PAGE_DATA})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(face_library, "get_settings", _stub_settings)

    response = client.post("/api/face-library/page", json={"current": 2, "size": 12, "keyword": "张三"})

    assert response.status_code == 200
    assert captured["url"] == f"{FACE_PHOTO_BASE}/face/es/label/facePage"
    assert captured["json"] == {"current": 2, "size": 12, "query": {"val": "张三"}}
    body = response.json()
    assert body["total"] == 1
    assert body["records"][0]["name"] == "zhangsan.jpg"


def test_face_page_without_keyword_sends_empty_query(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """不传关键字时 query 为空对象（不筛选）。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return FakeResponse({"code": "0", "msg": "success", "data": PAGE_DATA})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(face_library, "get_settings", _stub_settings)

    response = client.post("/api/face-library/page", json={"current": 1, "size": 12})

    assert response.status_code == 200
    assert captured["json"] == {"current": 1, "size": 12, "query": {}}


def test_face_page_business_error_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """外部业务码非 "0" 时返回 502 并携带外部 msg。"""
    monkeypatch.setattr(
        requests, "post", lambda url, json, timeout: FakeResponse({"code": "500", "msg": "ES 查询失败", "data": None})
    )
    monkeypatch.setattr(face_library, "get_settings", _stub_settings)

    response = client.post("/api/face-library/page", json={"current": 1, "size": 12})

    assert response.status_code == 502
    assert "ES 查询失败" in response.text


def test_face_page_connection_error_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """外部服务不可达时返回 502。"""

    def fake_post(url, json, timeout):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(face_library, "get_settings", _stub_settings)

    response = client.post("/api/face-library/page", json={"current": 1, "size": 12})

    assert response.status_code == 502


def test_face_page_not_configured_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """未配置服务地址时返回 500。"""
    monkeypatch.setattr(face_library, "get_settings", lambda: SimpleNamespace(face_photo_api_base_url=""))

    response = client.post("/api/face-library/page", json={"current": 1, "size": 12})

    assert response.status_code == 500
