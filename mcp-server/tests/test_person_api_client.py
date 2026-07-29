import asyncio
import json

import httpx

from app.person_api_client import PersonApiClient


def run(coro):
    return asyncio.run(coro)


def make_client(handler) -> PersonApiClient:
    return PersonApiClient("http://person-api.test", transport=httpx.MockTransport(handler))


def test_detect_persons_posts_image_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"code": 200, "data": {"status": "success"}})

    result = run(make_client(handler).detect_persons("http://example.test/query.jpg"))

    assert result["code"] == 200
    assert seen == {
        "method": "POST",
        "path": "/vlm-application/search/detectPersons",
        "body": {"image_url": "http://example.test/query.jpg"},
    }


def test_search_person_by_bbox_maps_mcp_fields_to_upstream_payload():
    seen = {}
    bbox = [{"x": 1, "y": 2}, {"x": 3, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 4}]

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"code": 200, "data": {"task_id": "task-1"}})

    result = run(
        make_client(handler).search_person_by_bbox(
            "http://example.test/query.jpg",
            bbox=bbox,
            search_method="vlm",
            start_time="2024-12-12 07:51:15",
            end_time="2026-12-12 08:50:17",
            similarity_threshold=0.72,
            top_k=5,
        )
    )

    assert result["data"]["task_id"] == "task-1"
    assert seen["path"] == "/vlm-application/search/searchPersonByBbox"
    assert seen["body"] == {
        "image_url": "http://example.test/query.jpg",
        "bbox": bbox,
        "search_method": "vlm",
        "start_time": "2024-12-12 07:51:15",
        "end_time": "2026-12-12 08:50:17",
        "similarity_threshold": 0.72,
        "top_k": 5,
    }


def test_get_person_search_result_uses_path_parameter():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json={"code": 200, "data": {"status": "pending"}})

    result = run(make_client(handler).get_person_search_result("task-1"))

    assert result["data"]["status"] == "pending"
    assert seen == {"method": "GET", "path": "/vlm-application/search/searchPersonResult/task-1"}


def test_gait_feature_compare_posts_array_and_preserves_4xx_payload():
    seen = {}
    persons = [{"id": "person_001", "isWalking": True}, {"id": "person_002", "isWalking": True}]

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(400, json={"msg": "未找到相似人员"})

    result = run(make_client(handler).gait_feature_compare(persons))

    assert result == {"upstreamStatusCode": 400, "msg": "未找到相似人员"}
    assert seen == {"path": "/vlm-application/gait/gaitFeaCompare", "body": persons}
