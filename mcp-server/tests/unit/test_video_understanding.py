"""视频理解结构化 MCP 工具的单元测试。"""

import asyncio
import json

import httpx
import pytest

import app.server as server
from app.video_understanding_client import DEFAULT_PROMPT, VideoUnderstandingClient


class FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.requests = []

    async def handle_async_request(self, request):
        self.requests.append(request)
        return httpx.Response(self.status_code, json=self.payload)


def make_client(payload, status_code=200):
    transport = FakeTransport(payload, status_code)
    client = VideoUnderstandingClient("http://understanding:8775/", timeout=5, transport=transport)
    return client, transport


def test_video_understanding_maps_payload_and_forwards_response():
    client, transport = make_client({"code": 0, "message": "success", "data": {"answer_status": "found"}})

    result = asyncio.run(
        client.structure(
            " http://minio/public/a.mp4 ",
            " 视频中是否有人跌倒 ",
            fps=1,
            segment_seconds=60,
            max_segments=2,
            height=480,
            prompt=" 请分析视频中的异常事件 ",
        )
    )

    assert result["code"] == 0
    request = transport.requests[0]
    assert request.url == "http://understanding:8775/api/v1/video-understanding/structure"
    assert json.loads(request.content) == {
        "video_url": "http://minio/public/a.mp4",
        "question": "视频中是否有人跌倒",
        "fps": 1,
        "segment_seconds": 60,
        "max_segments": 2,
        "height": 480,
        "prompt": "请分析视频中的异常事件",
    }


def test_video_understanding_clamps_numeric_fields():
    client, transport = make_client({"code": 0})

    asyncio.run(
        client.structure("http://minio/a.mp4", "问题", fps=0, segment_seconds=0, max_segments=-1, height=0)
    )

    payload = json.loads(transport.requests[0].content)
    assert payload["fps"] == 1
    assert payload["segment_seconds"] == 1
    # max_segments 为 0 表示全部分析，负数按 0 处理
    assert payload["max_segments"] == 0
    assert payload["height"] == 1


def test_video_understanding_prompt_defaults_when_blank():
    client, transport = make_client({"code": 0})

    asyncio.run(client.structure("http://minio/a.mp4", "问题", prompt="  "))

    payload = json.loads(transport.requests[0].content)
    assert payload["prompt"] == DEFAULT_PROMPT


@pytest.mark.parametrize("video_url, question", [("", "问题"), ("http://minio/a.mp4", "  ")])
def test_video_understanding_rejects_blank_required_fields(video_url, question):
    client, _ = make_client({"code": 0})
    with pytest.raises(ValueError, match="is required"):
        asyncio.run(client.structure(video_url, question))


def test_video_understanding_marks_upstream_client_error():
    client, _ = make_client({"code": "VALIDATION_001", "message": "invalid input", "data": None}, status_code=422)

    result = asyncio.run(client.structure("http://minio/a.mp4", "问题"))

    assert result["upstreamStatusCode"] == 422
    assert result["code"] == "VALIDATION_001"


def test_video_understanding_tool_is_registered(monkeypatch):
    captured = {}

    async def fake_structure(video_url, question, fps, segment_seconds, max_segments, height, prompt):
        captured["args"] = (video_url, question, fps, segment_seconds, max_segments, height, prompt)
        return {"code": 0}

    monkeypatch.setattr("app.tools.understanding.video_understanding_client.structure", fake_structure)

    result = asyncio.run(
        server.video_understanding(
            videoUrl="http://minio/a.mp4",
            question="有人跌倒吗",
            fps=1,
            segmentSeconds=30,
            maxSegments=0,
            height=360,
            prompt="分析异常事件",
        )
    )

    assert result == {"code": 0}
    assert captured["args"] == ("http://minio/a.mp4", "有人跌倒吗", 1, 30, 0, 360, "分析异常事件")
