"""文搜图 / 图搜图 MCP 工具的单元测试。"""

import asyncio

import pytest

import app.server as server
from app.tools import search as search_tools


class FakeRetrieveApi:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def text_search(self, message, start_time, end_time, location, page, page_size):
        self.calls.append((message, start_time, end_time, location, page, page_size))
        return self.payload


def test_text_search_images_maps_payload(monkeypatch):
    retrieve = FakeRetrieveApi({"code": 200, "data": {"total": 5, "items": []}})
    monkeypatch.setattr(search_tools, "retrieve_api", retrieve)

    result = asyncio.run(
        server.text_search_images(message="穿红衣服的人", startTime="2026-08-31 09:00", page=1, pageSize=500)
    )

    assert result["data"]["total"] == 5
    # pageSize 上限钳制在 RetrieveApiClient 内（见 test_retrieve_api_client），工具层原样透传
    assert retrieve.calls == [("穿红衣服的人", "2026-08-31 09:00", "", "", 1, 500)]


def test_text_search_images_requires_message():
    with pytest.raises(ValueError, match="message is required"):
        asyncio.run(server.text_search_images(message="  "))


class FakePersonApi:
    def __init__(self, detect=None, submit=None, results=None):
        self.detect = detect or {"data": {"status": "success", "detected_persons": [{"bbox": [{"x": 1, "y": 2}]}]}}
        # 与上游真实响应一致的双层嵌套：data.data.task_id
        self.submit = submit or {"data": {"status": "success", "message": "任务已提交", "data": {"task_id": "task-1"}}}
        self.results = list(results or [])
        self.submit_calls = []

    async def detect_persons(self, image_url):
        return self.detect

    async def search_person_by_bbox(self, image_url, **kwargs):
        self.submit_calls.append((image_url, kwargs))
        return self.submit

    async def get_person_search_result(self, task_id):
        if not self.results:
            return {"data": {"status": "pending"}}
        return self.results.pop(0)


def run_search(person_api, monkeypatch, **kwargs):
    monkeypatch.setattr(search_tools, "person_api", person_api)
    monkeypatch.setattr(search_tools, "POLL_INTERVAL_SECONDS", 0)
    kwargs.setdefault("imageUrl", "http://minio/a.jpg")
    return asyncio.run(server.search_person_by_image(**kwargs))


def test_search_person_by_image_detects_then_polls(monkeypatch):
    person_api = FakePersonApi(results=[{"data": {"status": "success", "data": {"similar_persons": [{"id": 1}]}}}])

    result = run_search(person_api, monkeypatch)

    assert result["data"]["data"]["similar_persons"] == [{"id": 1}]
    # 未传 bbox 时先走 detect_persons，取第一个人形框提交
    assert person_api.submit_calls[0][1]["bbox"] == [{"x": 1, "y": 2}]


def test_search_person_by_image_uses_given_bbox_without_detect(monkeypatch):
    person_api = FakePersonApi(
        detect={"data": {"status": "error", "message": "不应调用 detect"}},
        results=[{"data": {"status": "success", "data": {"similar_persons": []}}}],
    )
    bbox = [{"x": 10, "y": 20}]

    result = run_search(person_api, monkeypatch, bbox=bbox, searchMethod="vlm", topK=5)

    assert result["data"]["status"] == "success"
    assert person_api.submit_calls[0][1]["bbox"] == bbox
    assert person_api.submit_calls[0][1]["search_method"] == "vlm"
    assert person_api.submit_calls[0][1]["top_k"] == 5


def test_search_person_by_image_rejects_when_no_person_detected(monkeypatch):
    person_api = FakePersonApi(detect={"data": {"status": "error", "message": "未检测到人，请重新上传"}})

    with pytest.raises(ValueError, match="未检测到人"):
        run_search(person_api, monkeypatch)


def test_search_person_by_image_rejects_submit_failure(monkeypatch):
    person_api = FakePersonApi(submit={"data": {"status": "error", "message": "任务提交失败"}})

    with pytest.raises(ValueError, match="任务提交失败"):
        run_search(person_api, monkeypatch)


def test_search_person_by_image_rejects_task_error(monkeypatch):
    person_api = FakePersonApi(results=[{"data": {"status": "error", "message": "搜索任务失败"}}])

    with pytest.raises(ValueError, match="搜索任务失败"):
        run_search(person_api, monkeypatch)


def test_search_person_by_image_times_out_when_pending(monkeypatch):
    person_api = FakePersonApi(results=[{"data": {"status": "pending"}}] * 10)

    with pytest.raises(ValueError, match="超时"):
        run_search(person_api, monkeypatch, waitTimeoutSeconds=0.1)


class FakeTransport(__import__("httpx").AsyncBaseTransport):
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.requests = []

    async def handle_async_request(self, request):
        self.requests.append(request)
        return __import__("httpx").Response(self.status_code, json=self.payload)


def test_retrieve_api_client_clamps_and_maps_payload():
    import json

    from app.retrieve_api_client import RetrieveApiClient

    transport = FakeTransport({"code": 200, "data": {"total": 1}})
    client = RetrieveApiClient("http://retrieve:15011/", timeout=5, transport=transport)

    result = asyncio.run(
        client.text_search(" 穿红衣服的人 ", start_time="", end_time="", location="", page=0, page_size=500)
    )

    assert result["code"] == 200
    request = transport.requests[0]
    assert request.url == "http://retrieve:15011/v1/retrieve/query"
    assert json.loads(request.content) == {
        "message": "穿红衣服的人",
        "start_time": None,
        "end_time": None,
        "location": None,
        "page": 1,
        "page_size": 100,
    }
