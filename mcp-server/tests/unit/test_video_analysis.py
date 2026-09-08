"""MinIO 视频智能分析 MCP 工具的单元测试。"""

import asyncio
import json

import httpx
import pytest

import app.server as server
from app.video_analysis_client import VideoAnalysisClient


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
    client = VideoAnalysisClient("http://analysis:8775/", timeout=5, transport=transport)
    return client, transport


def test_analyze_minio_video_maps_payload_and_forwards_response():
    client, transport = make_client({"code": 0, "segments": [{"result": {"raw_text": "有人出现"}}]})

    result = asyncio.run(
        client.analyze_minio_video(
            " http://minio/public/a.mp4 ",
            " 是否有人出现 ",
            fps=1,
            segment_seconds=60,
            max_segments=2,
            height=480,
        )
    )

    assert result["code"] == 0
    request = transport.requests[0]
    assert request.url == "http://analysis:8775/analyze_minio_video"
    assert json.loads(request.content) == {
        "video_url": "http://minio/public/a.mp4",
        "fps": 1,
        "segment_seconds": 60,
        "max_segments": 2,
        "height": 480,
        "prompt": "是否有人出现",
    }


def test_analyze_minio_video_clamps_numeric_fields():
    client, transport = make_client({"code": 0})

    asyncio.run(
        client.analyze_minio_video("http://minio/a.mp4", "分析", fps=0, segment_seconds=0, max_segments=0, height=0)
    )

    payload = json.loads(transport.requests[0].content)
    assert payload["fps"] == 1
    assert payload["segment_seconds"] == 1
    assert payload["max_segments"] == 1
    assert payload["height"] == 1


@pytest.mark.parametrize("video_url, prompt", [("", "分析"), ("http://minio/a.mp4", "  ")])
def test_analyze_minio_video_rejects_blank_required_fields(video_url, prompt):
    client, _ = make_client({"code": 0})
    with pytest.raises(ValueError, match="is required"):
        asyncio.run(client.analyze_minio_video(video_url, prompt))


def test_analyze_minio_video_marks_upstream_client_error():
    client, _ = make_client({"message": "bad request"}, status_code=400)

    result = asyncio.run(client.analyze_minio_video("http://minio/a.mp4", "分析"))

    assert result["upstreamStatusCode"] == 400


def test_analyze_minio_video_tool_is_registered(monkeypatch):
    captured = {}

    async def fake_analyze(video_url, prompt, fps, segment_seconds, max_segments, height):
        captured["args"] = (video_url, prompt, fps, segment_seconds, max_segments, height)
        return {"code": 0}

    monkeypatch.setattr("app.tools.analysis.video_analysis.analyze_minio_video", fake_analyze)

    result = asyncio.run(
        server.analyze_minio_video(
            videoUrl="http://minio/a.mp4",
            prompt="分析",
            fps=1,
            segmentSeconds=30,
            maxSegments=2,
            height=360,
        )
    )

    assert result == {"code": 0}
    assert captured["args"] == ("http://minio/a.mp4", "分析", 1, 30, 2, 360)
