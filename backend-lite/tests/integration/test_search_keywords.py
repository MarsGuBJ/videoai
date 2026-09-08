"""搜索关键词记录与统计测试：查询接口挂钩写入 + 列表/统计端点契约。"""

from fastapi.testclient import TestClient

import app.api.routers.person_search as person_search_router
import app.api.routers.video_analysis as video_analysis_router
import app.services.search_keywords as search_keywords_service


def _stub_persist(monkeypatch):
    monkeypatch.setattr(search_keywords_service, "persist_search_keyword", lambda record: None)


def _do_text_image_query(client: TestClient, monkeypatch, message: str = "穿红衣服的人"):
    _stub_persist(monkeypatch)
    monkeypatch.setattr(person_search_router, "retrieve_api_post", lambda path, payload: {"code": 0, "data": []})
    response = client.post("/api/text-search/query", json={"message": message})
    assert response.status_code == 200


def _do_text_video_query(client: TestClient, monkeypatch, prompt: str = "白色车辆"):
    _stub_persist(monkeypatch)
    monkeypatch.setattr(video_analysis_router, "video_analysis_api_post", lambda path, payload: {"code": 0})
    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": "http://minio/demo.mp4", "prompt": prompt},
    )
    assert response.status_code == 200


def test_text_image_query_records_keyword(client: TestClient, monkeypatch):
    _do_text_image_query(client, monkeypatch)

    listed = client.get("/api/search-keywords").json()
    assert len(listed) == 1
    assert listed[0]["keyword"] == "穿红衣服的人"
    assert listed[0]["searchType"] == "text_image"
    assert listed[0]["id"]
    assert listed[0]["createdAt"]


def test_text_video_query_records_prompt(client: TestClient, monkeypatch):
    _do_text_video_query(client, monkeypatch)

    listed = client.get("/api/search-keywords").json()
    assert len(listed) == 1
    assert listed[0]["keyword"] == "白色车辆"
    assert listed[0]["searchType"] == "text_video"


def test_list_returns_newest_first(client: TestClient, monkeypatch):
    _do_text_image_query(client, monkeypatch, message="第一条")
    _do_text_video_query(client, monkeypatch, prompt="第二条")

    listed = client.get("/api/search-keywords").json()
    assert [item["keyword"] for item in listed] == ["第二条", "第一条"]


def test_stats_aggregates_count_and_filters_by_type(client: TestClient, monkeypatch):
    _do_text_image_query(client, monkeypatch, message="安全帽")
    _do_text_image_query(client, monkeypatch, message="安全帽")
    _do_text_video_query(client, monkeypatch, prompt="白色车辆")

    stats = client.get("/api/search-keywords/stats").json()
    assert [(item["keyword"], item["count"]) for item in stats] == [("安全帽", 2), ("白色车辆", 1)]
    assert stats[0]["searchType"] == "text_image"
    assert stats[0]["lastSearchedAt"]

    filtered = client.get("/api/search-keywords/stats", params={"searchType": "text_video"}).json()
    assert [(item["keyword"], item["count"]) for item in filtered] == [("白色车辆", 1)]


def test_blank_keyword_not_recorded(client: TestClient, monkeypatch):
    _stub_persist(monkeypatch)
    monkeypatch.setattr(person_search_router, "retrieve_api_post", lambda path, payload: {"code": 0})
    client.post("/api/text-search/query", json={"message": "   "})

    assert client.get("/api/search-keywords").json() == []


def test_stats_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/search-keywords/stats")

    assert response.status_code == 200
    assert response.json() == []
