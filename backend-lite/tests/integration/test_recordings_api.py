"""录像检索 / 回放 / 下载代理接口的集成测试。"""

import pytest
import requests
from fastapi.testclient import TestClient

from app.services import camera_cache

BASE_BODY = {"cameraId": "cam-1", "startTime": "2026-08-31 10:00", "endTime": "2026-08-31 10:02"}

SEGMENT = {
    "recordingId": "rec-1",
    "cameraId": "cam-1",
    "cameraName": "东门",
    "trackId": "201",
    "startTime": "2026-08-31 10:00",
    "endTime": "2026-08-31 10:02",
    "source": "nvr",
    "metadata": {"channel": 1},
}

SEARCH_PAYLOAD = {"data": [SEGMENT], "xml": "<xml/>", "searchedTrackIds": ["201"], "failedTrackIds": {}}

STREAM_PAYLOAD = {
    "url": "http://192.168.11.194:9000/public/recordings/streams/rec-1.flv",
    "format": "flv",
    "expiresAt": "2026-08-31 11:00",
    "source": "nvr",
    "metadata": {},
    "xml": "<xml/>",
}

DOWNLOAD_PAYLOAD = {
    "data": [
        {
            "recordingId": "rec-1",
            "cameraId": "cam-1",
            "startTime": "2026-08-31 10:00",
            "endTime": "2026-08-31 10:02",
            "url": "http://192.168.11.194:9000/public/recordings/exports/201/a.mp4",
            "format": "mp4",
        }
    ]
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self.payload


class FakeCamera:
    def __init__(self, nvr_track_id="201", nvr_channel="1"):
        self.nvrTrackId = nvr_track_id
        self.nvrChannel = nvr_channel


@pytest.fixture(autouse=True)
def bound_camera(monkeypatch: pytest.MonkeyPatch):
    """默认摄像头存在且已绑定 NVR，用例可自行覆盖。"""
    monkeypatch.setattr(camera_cache, "get", lambda camera_id: FakeCamera())


def _fake_mcp_post(monkeypatch: pytest.MonkeyPatch, responses: dict[str, object], captured: list | None = None):
    """按 URL 后缀分发 MCP 响应；responses 值为 dict（200）或 requests 异常实例。"""

    def fake_post(url, json, timeout):
        if captured is not None:
            captured.append({"url": url, "json": json, "timeout": timeout})
        for suffix, response in responses.items():
            if url.endswith(suffix):
                if isinstance(response, Exception):
                    raise response
                return FakeResponse(response)
        raise AssertionError(f"unexpected MCP url: {url}")

    monkeypatch.setattr(requests, "post", fake_post)


def test_search_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """检索成功时透传录像段列表。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {"/search_recordings-http": SEARCH_PAYLOAD}, captured)

    response = client.post("/api/recordings/search", json=BASE_BODY)

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["recordingId"] == "rec-1"
    assert body["data"][0]["url"] is None
    call = captured[0]
    assert call["url"] == "http://192.168.11.194:8097/search_recordings-http"
    assert call["json"] == {
        "cameraId": "cam-1",
        "startTime": "2026-08-31 10:00",
        "endTime": "2026-08-31 10:02",
        "autoProxy": False,
        "streamFormat": "flv",
    }
    assert call["timeout"] == 30


def test_search_camera_not_found(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """摄像头不在缓存中时返回 404。"""
    monkeypatch.setattr(camera_cache, "get", lambda camera_id: None)

    response = client.post("/api/recordings/search", json=BASE_BODY)

    assert response.status_code == 404


@pytest.mark.parametrize("camera", [FakeCamera(None, None), FakeCamera("", "  ")])
def test_search_unbound_camera_still_proxied(client: TestClient, monkeypatch: pytest.MonkeyPatch, camera: FakeCamera):
    """未绑定 NVR 的摄像头不再本地 400：透传 MCP（由 MCP 反查其所属 NVR，未命中时报参数错误）。"""
    monkeypatch.setattr(camera_cache, "get", lambda camera_id: camera)
    captured: list = []
    _fake_mcp_post(
        monkeypatch,
        {"/search_recordings-http": {"data": [], "xml": "", "searchedTrackIds": [], "failedTrackIds": {}}},
        captured,
    )

    response = client.post("/api/recordings/search", json=BASE_BODY)

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert captured[0]["json"]["cameraId"] == "cam-1"


def test_stream_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """检索到录像后取第一段换取 FLV 回放地址。"""
    captured: list = []
    _fake_mcp_post(
        monkeypatch,
        {"/search_recordings-http": SEARCH_PAYLOAD, "/get_recording_stream-http": STREAM_PAYLOAD},
        captured,
    )

    response = client.post("/api/recordings/stream", json=BASE_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["url"].endswith("rec-1.flv")
    assert body["format"] == "flv"
    assert body["expiresAt"] == "2026-08-31 11:00"
    stream_call = captured[1]
    assert stream_call["url"].endswith("/get_recording_stream-http")
    assert stream_call["json"] == {"recordingId": "rec-1", "format": "flv", "speed": 1.0}
    assert stream_call["timeout"] == 60


def test_stream_no_recording_returns_404(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """时段无录像时返回 404。"""
    _fake_mcp_post(
        monkeypatch,
        {"/search_recordings-http": {"data": [], "xml": "", "searchedTrackIds": [], "failedTrackIds": {}}},
    )

    response = client.post("/api/recordings/stream", json=BASE_BODY)

    assert response.status_code == 404
    assert response.json()["detail"] == "该时段无录像"


def test_stream_passes_speed_to_mcp(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """倍速参数透传到 MCP 的 get_recording_stream。"""
    captured: list = []
    _fake_mcp_post(
        monkeypatch,
        {"/search_recordings-http": SEARCH_PAYLOAD, "/get_recording_stream-http": STREAM_PAYLOAD},
        captured,
    )

    response = client.post("/api/recordings/stream", json={**BASE_BODY, "speed": 8})

    assert response.status_code == 200
    assert captured[1]["json"] == {"recordingId": "rec-1", "format": "flv", "speed": 8.0}


def test_stream_rejects_unsupported_speed(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """倍速不在 NVR 实测支持档位时返回 400，不调用 MCP。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {}, captured)

    response = client.post("/api/recordings/stream", json={**BASE_BODY, "speed": 3})

    assert response.status_code == 400
    assert captured == []


def test_download_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """下载成功时返回 MP4 地址。"""
    captured: list = []
    _fake_mcp_post(monkeypatch, {"/download_recording-http": DOWNLOAD_PAYLOAD}, captured)

    response = client.post("/api/recordings/download", json=BASE_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["url"].endswith("a.mp4")
    assert body["format"] == "mp4"
    call = captured[0]
    assert call["url"].endswith("/download_recording-http")
    assert call["json"] == {"cameraId": "cam-1", "startTime": "2026-08-31 10:00", "endTime": "2026-08-31 10:02"}
    assert call["timeout"] == 1800


def test_download_empty_data_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """下载结果为空时返回 502。"""
    _fake_mcp_post(monkeypatch, {"/download_recording-http": {"data": []}})

    response = client.post("/api/recordings/download", json=BASE_BODY)

    assert response.status_code == 502


@pytest.mark.parametrize("endpoint", ["/api/recordings/search", "/api/recordings/stream", "/api/recordings/download"])
def test_mcp_error_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch, endpoint: str):
    """MCP 返回 error 负载时返回 502，detail 带 MCP message。"""
    _fake_mcp_post(
        monkeypatch,
        {
            "/search_recordings-http": {"error": {"type": "NvrOffline", "message": "NVR 连接失败"}},
            "/download_recording-http": {"error": {"type": "NvrOffline", "message": "NVR 连接失败"}},
        },
    )

    response = client.post(endpoint, json=BASE_BODY)

    assert response.status_code == 502
    assert "NVR 连接失败" in response.json()["detail"]


def test_mcp_param_error_returns_400(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 报参数类错误时透传为 400。"""
    _fake_mcp_post(
        monkeypatch,
        {"/search_recordings-http": {"error": {"type": "InvalidParams", "message": "startTime 晚于 endTime"}}},
    )

    response = client.post("/api/recordings/search", json=BASE_BODY)

    assert response.status_code == 400
    assert "startTime 晚于 endTime" in response.json()["detail"]


def test_mcp_unavailable_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 不可达时返回 502。"""
    _fake_mcp_post(monkeypatch, {"/search_recordings-http": requests.ConnectionError("refused")})

    response = client.post("/api/recordings/search", json=BASE_BODY)

    assert response.status_code == 502
