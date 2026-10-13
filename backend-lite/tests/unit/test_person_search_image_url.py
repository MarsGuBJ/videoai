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
    # 2026-09 上游重构：searchPersonByBbox 下线，改调详版 searchPersonFull
    assert captured["url"] == f"{PERSON_BASE}/vlm-application/search/searchPersonFull"
    assert captured["json"]["image_url"] == (
        f"{PUBLIC_BASE}/api/video-analysis/frame?videoUrl=http://minio/a.mp4&seconds=12"
    )
    assert captured["json"]["similarity_threshold"] == 0.82
    assert captured["json"]["top_k"] == 50


def test_search_by_bbox_forwards_attribute_filters(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """search-by-bbox：人员属性筛选（性别/年龄段/上衣颜色）映射为上游 sex/age/top_color。"""
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
            "imageUrl": "http://minio/a.jpg",
            "searchMethod": "reid",
            "sex": "男",
            "age": "青年",
            "topColor": "白色",
        },
    )

    assert response.status_code == 200
    assert captured["json"]["sex"] == "男"
    assert captured["json"]["age"] == "青年"
    assert captured["json"]["top_color"] == "白色"


def test_search_by_bbox_omits_empty_attribute_filters(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """search-by-bbox：属性筛选不传/传空时不往上游带这些字段（上游语义：不传 = 不过滤）。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return FakeResponse({"code": "00000", "data": {"status": "success"}})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))

    response = client.post(
        "/api/person-search/search-by-bbox",
        json={"imageUrl": "http://minio/a.jpg", "searchMethod": "reid", "sex": "", "topColor": None},
    )

    assert response.status_code == 200
    assert "sex" not in captured["json"]
    assert "age" not in captured["json"]
    assert "top_color" not in captured["json"]


@pytest.mark.parametrize("missing_status", [404, 500])
def test_search_by_bbox_falls_back_to_legacy_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    missing_status: int,
):
    """旧版上游镜像没有 searchPersonFull 路由（Flask 统一回 404/500）时自动回退旧版提交。

    团结湖现场 172.17.136.189:15501 部署的 vlm-application v3.20260915-1020 即此情况：
    未注册路由被 Flask ErrorHandler 包成 HTTP 500 + {"code":"00001",...}。
    """
    captured_urls = []

    def fake_post(url, json, timeout):
        captured_urls.append(url)
        if url.endswith("searchPersonFull"):
            return FakeResponse(
                {"code": "00001", "data": None, "message": "操作失败", "status": False},
                status_code=missing_status,
            )
        return FakeResponse(
            {"code": "00000", "data": {"data": {"task_id": "t-1"}}, "message": "任务已提交", "status": True}
        )

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))

    response = client.post(
        "/api/person-search/search-by-bbox",
        json={"imageUrl": f"{PUBLIC_BASE}/api/assets/query-images/a.jpg"},
    )

    assert response.status_code == 200
    assert captured_urls == [
        f"{PERSON_BASE}/vlm-application/search/searchPersonFull",
        f"{PERSON_BASE}/vlm-application/search/searchPersonByBbox",
    ]
    assert response.json()["data"]["data"]["task_id"] == "t-1"


def test_search_by_bbox_does_not_fallback_on_business_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """详版返回 400 这类业务错误时不回退，单次调用直接透传。"""
    captured_urls = []

    def fake_post(url, json, timeout):
        captured_urls.append(url)
        return FakeResponse({"detail": "similarity_threshold out of range"}, status_code=400)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))

    response = client.post(
        "/api/person-search/search-by-bbox",
        json={"imageUrl": f"{PUBLIC_BASE}/api/assets/query-images/a.jpg"},
    )

    assert response.status_code == 400
    assert len(captured_urls) == 1
    assert captured_urls[0].endswith("searchPersonFull")


def test_search_by_bbox_fallback_failure_keeps_original_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """回退后旧版接口也失败时，抛详版的原始报错，避免旧版错误掩盖根因。"""
    def fake_post(url, json, timeout):
        if url.endswith("searchPersonFull"):
            return FakeResponse({"code": "00001", "data": None, "message": "操作失败", "status": False}, status_code=500)
        return FakeResponse({"message": "legacy unavailable"}, status_code=502)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(person_search, "get_settings", lambda: _stub_settings(PUBLIC_BASE))

    response = client.post(
        "/api/person-search/search-by-bbox",
        json={"imageUrl": f"{PUBLIC_BASE}/api/assets/query-images/a.jpg"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == {"code": "00001", "data": None, "message": "操作失败", "status": False}
