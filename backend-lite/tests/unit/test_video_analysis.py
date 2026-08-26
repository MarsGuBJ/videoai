"""MinIO 视频智能分析代理的单元测试。"""

import pytest
import requests
from fastapi.testclient import TestClient

from app.services import video_analysis


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self.payload


def test_analyze_proxy_maps_payload_and_forwards_response(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """camelCase 入参映射为 snake_case，上游 2xx 响应原样透传。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse({"code": 0, "data": {"result": "有人出现"}})

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": " http://192.168.11.194:9000/public/a.mp4 ", "prompt": "是否有人出现"},
    )

    assert response.status_code == 200
    assert response.json() == {"code": 0, "data": {"result": "有人出现"}}
    assert captured["url"] == "http://192.168.11.192:8775/analyze_minio_video"
    assert captured["json"] == {
        "video_url": "http://192.168.11.194:9000/public/a.mp4",
        "fps": 1,
        "segment_seconds": 60,
        "max_segments": 1,
        "height": 480,
        "prompt": "是否有人出现",
    }
    assert captured["timeout"] == video_analysis.VIDEO_ANALYSIS_API_TIMEOUT_SECONDS


def test_analyze_proxy_clamps_numeric_fields(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """数值字段小于 1 时按 1 处理。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return FakeResponse({"code": 0})

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={
            "videoUrl": "http://192.168.11.194:9000/public/a.mp4",
            "prompt": "分析",
            "fps": 0,
            "segmentSeconds": 0,
            "maxSegments": 0,
            "height": 0,
        },
    )

    assert response.status_code == 200
    assert captured["json"]["fps"] == 1
    assert captured["json"]["segment_seconds"] == 1
    assert captured["json"]["max_segments"] == 1
    assert captured["json"]["height"] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"videoUrl": "", "prompt": "分析"},
        {"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "prompt": "  "},
    ],
)
def test_analyze_proxy_rejects_blank_required_fields(client: TestClient, payload):
    """videoUrl / prompt 为空白时返回 400。"""
    response = client.post("/api/video-analysis/analyze", json=payload)
    assert response.status_code == 400


def test_analyze_proxy_passes_through_upstream_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游非 2xx 时按原状态码透传。"""

    def fake_post(url, json, timeout):
        return FakeResponse({"message": "boom"}, status_code=500)

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "prompt": "分析"},
    )

    assert response.status_code == 500


def test_analyze_proxy_upstream_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游不可达时返回 502。"""

    def fake_post(url, json, timeout):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "prompt": "分析"},
    )

    assert response.status_code == 502
