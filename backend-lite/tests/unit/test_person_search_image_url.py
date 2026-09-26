"""以图搜人代理的图片地址归一化测试。

背景：外部以图搜人服务只接受 http(s) 地址或 base64，前端（文搜视频页签）会传
后端自身的相对资源路径，转发前必须补全为公网绝对地址，否则检索报 Incorrect padding。
"""

from types import SimpleNamespace

import pytest
import requests
from fastapi.testclient import TestClient

from app.services import person_search

PUBLIC_BASE = "http://172.17.136.189:8081"
PERSON_BASE = "http://172.17.136.189:15501"


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self.payload


def _stub_settings(public_url):
    return SimpleNamespace(backend_public_url=public_url, person_api_base_url=PERSON_BASE)


def test_absolutize_relative_path(monkeypatch: pytest.MonkeyPatch):
    """相对资源路径按 BACKEND_PUBLIC_URL 补全。"""
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))
    assert (
        person_search.absolutize_image_url("/api/assets/query-images/a.jpg")
        == f"{PUBLIC_BASE}/api/assets/query-images/a.jpg"
    )


def test_absolutize_keeps_absolute_and_data_urls(monkeypatch: pytest.MonkeyPatch):
    """绝对地址、data:/blob: 原样透传，避免二次拼接。"""
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))
    for value in (
        "http://172.17.136.189:8081/api/assets/query-images/a.jpg",
        "https://example.com/a.jpg",
        "HTTP://example.com/a.jpg",
        "data:image/jpeg;base64,AAAA",
        "blob:http://172.17.136.189:5173/abc",
        "//cdn.example.com/a.jpg",
        "not-a-path.jpg",
    ):
        assert person_search.absolutize_image_url(value) == value


def test_absolutize_relative_path_with_absolute_url_query(monkeypatch: pytest.MonkeyPatch):
    """相对路径的查询串里带 http:// 时不能被误判为绝对地址（前端截帧地址就长这样）。"""
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))
    value = "/api/video-analysis/frame?videoUrl=http://minio/a.mp4&seconds=12"
    assert person_search.absolutize_image_url(value) == f"{PUBLIC_BASE}{value}"


def test_absolutize_without_public_base_keeps_path(monkeypatch: pytest.MonkeyPatch):
    """未配置公网地址时不强行拼接，保持原值。"""
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(None))
    assert person_search.absolutize_image_url("/api/assets/query-images/a.jpg") == "/api/assets/query-images/a.jpg"


def test_detect_persons_forwards_absolute_image_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """detect-persons：相对路径转发给外部服务前补全为绝对地址。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"code": "00000", "data": {"status": "success"}})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))

    response = client.post("/api/person-search/detect-persons", json={"imageUrl": "/api/assets/query-images/a.jpg"})

    assert response.status_code == 200
    assert captured["url"] == f"{PERSON_BASE}/vlm-application/search/detectPersons"
    assert captured["json"] == {"image_url": f"{PUBLIC_BASE}/api/assets/query-images/a.jpg"}


def test_search_by_bbox_forwards_absolute_image_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """search-by-bbox：相对截帧地址同样补全，其余参数照旧映射为 snake_case。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"code": "00000", "data": {"status": "success"}})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))

    response = client.post(
        "/api/person-search/search-by-bbox",
        json={
            "imageUrl": "/api/video-analysis/frame?videoUrl=http://minio/a.mp4&seconds=12",
            "searchMethod": "reid",
            "similarityThreshold": 0.82,
            "topK": 50,
        },
    )

    assert response.status_code == 200
    assert captured["json"]["image_url"] == (
        f"{PUBLIC_BASE}/api/video-analysis/frame?videoUrl=http://minio/a.mp4&seconds=12"
    )
    assert captured["json"]["similarity_threshold"] == 0.82
    assert captured["json"]["top_k"] == 50
