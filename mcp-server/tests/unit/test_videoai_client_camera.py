"""get_camera 的 cameraId 校验与上游 404 映射。

背景：backend-media（Java）对非 UUID 的 cameraId 会返回类型转换 500，
若不拦截，MCP 的 search_recordings-http / recording-live 会把调用方的
输入错误放大成 500 "internal server error"。这类输入错误必须是 400（ValueError）。
"""

import asyncio

import httpx
import pytest

from app import videoai_client
from app.videoai_client import CameraNotFoundError, VideoAiClient, normalize_camera_id

VALID_ID = "f9fc40a1-35d4-4c90-9dec-cdbf64239560"

CAMERA_PAYLOAD = {
    "id": VALID_ID,
    "name": "1205会议室",
    "sourceUrl": "rtsp://admin:secret@192.168.11.65:554/Streaming/Channels/101",
    "streamApp": "live",
    "streamName": "nvr65",
    "status": "online",
    "playbackUrl": "http://media.test/playback/nvr65.m3u8",
    "nvrTrackId": "101",
    "createdAt": "2026-01-01T00:00:00+08:00",
    "updatedAt": "2026-01-01T00:00:00+08:00",
}


def run(coro):
    return asyncio.run(coro)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Server error '{self.status_code}'",
                request=httpx.Request("GET", "http://backend-media.test"),
                response=httpx.Response(self.status_code),
            )


class FakeAsyncClient:
    """替身 httpx.AsyncClient：记录请求 URL，按预设状态码响应。"""

    instances: list["FakeAsyncClient"] = []
    status_code = 200
    payload: dict = {}

    def __init__(self, **_kwargs) -> None:
        self.requests: list[str] = []
        FakeAsyncClient.instances.append(self)

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_exc) -> bool:
        return False

    async def get(self, url: str) -> FakeResponse:
        self.requests.append(url)
        return FakeResponse(FakeAsyncClient.status_code, FakeAsyncClient.payload)


@pytest.fixture
def fake_http(monkeypatch):
    """把 httpx.AsyncClient 换成替身，并清理上一次用例的记录。"""
    FakeAsyncClient.instances = []
    FakeAsyncClient.status_code = 200
    FakeAsyncClient.payload = {}
    monkeypatch.setattr(videoai_client.httpx, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


@pytest.mark.parametrize("camera_id", ["not-exist-camera", "", "   ", "12345", None])
def test_normalize_camera_id_rejects_non_uuid(camera_id):
    with pytest.raises(CameraNotFoundError) as excinfo:
        normalize_camera_id(camera_id)
    assert "not a valid camera id" in str(excinfo.value)
    # 子类 ValueError：MCP/HTTP 层按参数错误返回 400
    assert isinstance(excinfo.value, ValueError)


def test_normalize_camera_id_canonicalizes_uuid():
    assert normalize_camera_id(f"  {VALID_ID.upper()}  ") == VALID_ID
    assert normalize_camera_id("{" + VALID_ID + "}") == VALID_ID


def test_get_camera_skips_upstream_call_for_invalid_id(fake_http):
    client = VideoAiClient("http://backend.test", media_base_url="http://backend-media.test")
    with pytest.raises(CameraNotFoundError):
        run(client.get_camera("not-exist-camera"))
    # 非法 cameraId 不发起上游请求，避免上游 UUID 类型转换 500
    assert fake_http.instances == []


def test_get_camera_maps_upstream_404_to_client_error(fake_http):
    fake_http.status_code = 404
    client = VideoAiClient("http://backend.test", media_base_url="http://backend-media.test")
    with pytest.raises(CameraNotFoundError) as excinfo:
        run(client.get_camera(VALID_ID))
    assert VALID_ID in str(excinfo.value)
    assert fake_http.instances[0].requests == [f"http://backend-media.test/api/cameras/{VALID_ID}"]


def test_get_camera_returns_camera_on_success(fake_http):
    fake_http.payload = CAMERA_PAYLOAD
    client = VideoAiClient("http://backend.test", media_base_url="http://backend-media.test")
    camera = run(client.get_camera(VALID_ID))
    assert camera.id == VALID_ID
    assert camera.track_id  # 直连 IPC 的 sourceUrl 仍可用于反查 NVR 通道


def test_get_camera_keeps_upstream_5xx_as_server_error(fake_http):
    """真正的上游故障仍应是 5xx（HTTPStatusError），不要被误判成 400。"""
    fake_http.status_code = 503
    client = VideoAiClient("http://backend.test", media_base_url="http://backend-media.test")
    with pytest.raises(httpx.HTTPStatusError):
        run(client.get_camera(VALID_ID))
