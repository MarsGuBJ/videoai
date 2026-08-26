import threading
from uuid import UUID

import pytest
import requests

from app.services import camera_cache

CAMERA_ID = "11111111-1111-1111-1111-111111111111"
NOW = "2026-08-24T00:00:00Z"


def camera_payload(camera_id=CAMERA_ID, name="Camera 1", status="RUNNING"):
    return {
        "id": camera_id,
        "name": name,
        "sourceUrl": "rtsp://admin:password@10.10.0.93/Streaming/Channels/101",
        "streamApp": "live",
        "streamName": "camera-1",
        "status": status,
        "playbackUrl": "http://zlm/live/camera-1.live.flv",
        "createdAt": NOW,
        "updatedAt": NOW,
    }


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


@pytest.fixture(autouse=True)
def isolate_cache():
    with camera_cache._data_lock:
        original = dict(camera_cache._cameras)
        camera_cache._cameras.clear()
    yield
    camera_cache.stop()
    with camera_cache._data_lock:
        camera_cache._cameras.clear()
        camera_cache._cameras.update(original)


def test_refresh_populates_cache_and_get_returns_camera(monkeypatch):
    monkeypatch.setattr(
        camera_cache.requests,
        "get",
        lambda url, timeout: FakeResponse([camera_payload()]),
    )

    assert camera_cache.refresh() is True

    cameras = camera_cache.all()
    assert len(cameras) == 1
    camera = cameras[0]
    assert camera.id == UUID(CAMERA_ID)
    assert camera.name == "Camera 1"
    assert camera.streamName == "camera-1"
    assert camera_cache.get(CAMERA_ID) is camera
    assert camera_cache.get(UUID(CAMERA_ID)) is camera
    assert camera_cache.get("00000000-0000-0000-0000-000000000000") is None


def test_refresh_uses_media_backend_url(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return FakeResponse([])

    monkeypatch.setattr(camera_cache.requests, "get", fake_get)
    monkeypatch.setattr(camera_cache, "MEDIA_BACKEND_URL", "http://backend-media:8081")

    assert camera_cache.refresh() is True
    assert calls == ["http://backend-media:8081/api/cameras"]


def test_failed_refresh_keeps_previous_data(monkeypatch):
    monkeypatch.setattr(
        camera_cache.requests,
        "get",
        lambda url, timeout: FakeResponse([camera_payload()]),
    )
    assert camera_cache.refresh() is True
    assert len(camera_cache.all()) == 1

    def fail_get(url, timeout):
        raise requests.ConnectionError("backend down")

    monkeypatch.setattr(camera_cache.requests, "get", fail_get)

    assert camera_cache.refresh() is False
    cameras = camera_cache.all()
    assert len(cameras) == 1
    assert cameras[0].name == "Camera 1"


def test_http_error_refresh_keeps_previous_data(monkeypatch):
    monkeypatch.setattr(
        camera_cache.requests,
        "get",
        lambda url, timeout: FakeResponse([camera_payload()]),
    )
    assert camera_cache.refresh() is True

    monkeypatch.setattr(
        camera_cache.requests,
        "get",
        lambda url, timeout: FakeResponse({"detail": "boom"}, status_code=500),
    )

    assert camera_cache.refresh() is False
    assert len(camera_cache.all()) == 1


def test_malformed_entries_are_skipped(monkeypatch):
    monkeypatch.setattr(
        camera_cache.requests,
        "get",
        lambda url, timeout: FakeResponse([camera_payload(), {"id": "not-a-uuid"}]),
    )

    assert camera_cache.refresh() is True
    assert [camera.name for camera in camera_cache.all()] == ["Camera 1"]


def test_start_is_idempotent_and_thread_refreshes(monkeypatch):
    refreshes = threading.Event()

    def fake_refresh():
        refreshes.set()
        return True

    monkeypatch.setattr(camera_cache, "refresh", fake_refresh)
    monkeypatch.setattr(camera_cache, "REFRESH_INTERVAL_SECONDS", 3600)

    camera_cache.start()
    first_thread = camera_cache._thread
    camera_cache.start()

    assert camera_cache._thread is first_thread
    assert refreshes.wait(timeout=2)

    camera_cache.stop()
    assert not first_thread.is_alive()
