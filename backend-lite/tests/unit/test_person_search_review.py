"""大模型二次研判代理（/api/person-search/review）的报错可读性测试。

背景：旧版上游镜像（无 searchPersonReview 路由，如 v3.20260915）的 Flask
ErrorHandler 会把未注册路由包成 HTTP 500 {"code":"00001","message":"操作失败"}，
页面只弹「操作失败」无从排查；代理层识别该特征转为 501 + 可读提示。
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.routers import person_search as person_search_router

PAYLOAD = {
    "imageUrl": "http://example.com/a.jpg",
    "bbox": [{"x": 1, "y": 2}, {"x": 3, "y": 4}],
    "esIds": ["doc-1"],
}


def test_review_old_upstream_returns_readable_501(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游无 searchPersonReview 路由（500 + code 00001）时返回 501 与可读提示。"""

    def fake_post(path, payload):
        raise HTTPException(status_code=500, detail={"code": "00001", "message": "操作失败"})

    monkeypatch.setattr(person_search_router, "person_api_post", fake_post)
    response = client.post("/api/person-search/review", json=PAYLOAD)
    assert response.status_code == 501
    assert "版本过旧" in response.json()["detail"]


def test_review_other_upstream_errors_passthrough(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """非「路由缺失」特征的上游错误按原状态码透传。"""

    def fake_post(path, payload):
        raise HTTPException(status_code=502, detail="Person search API unavailable: boom")

    monkeypatch.setattr(person_search_router, "person_api_post", fake_post)
    response = client.post("/api/person-search/review", json=PAYLOAD)
    assert response.status_code == 502


def test_review_success_passthrough(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游正常返回时原样透传，并校验转发字段。"""

    captured = {}

    def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"code": "0", "data": {"task_id": "t-1"}}

    monkeypatch.setattr(person_search_router, "person_api_post", fake_post)
    response = client.post("/api/person-search/review", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json()["data"]["task_id"] == "t-1"
    assert captured["path"] == "/vlm-application/search/searchPersonReview"
    assert captured["payload"]["es_ids"] == ["doc-1"]
    assert "review" not in captured["payload"]


def test_review_auto_flag_forwarded(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """搜索后自动研判时，review=true 透传给上游。"""

    captured = {}

    def fake_post(path, payload):
        captured["payload"] = payload
        return {"code": "0", "data": {"task_id": "t-1"}}

    monkeypatch.setattr(person_search_router, "person_api_post", fake_post)
    response = client.post("/api/person-search/review", json={**PAYLOAD, "review": True})
    assert response.status_code == 200
    assert captured["payload"]["review"] is True
