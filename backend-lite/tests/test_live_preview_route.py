import asyncio
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException

import main
from preview_relay import PreviewRelayError, PreviewRelayTimeout


SOURCE_URL = "rtsp://admin:password@10.10.0.93/Streaming/Channels/101"


class FakePreviewManager:
    def __init__(self, error=None):
        self.error = error
        self.acquired = []
        self.released = []
        self.stopped = []

    def acquire(self, stream_name, source_url):
        self.acquired.append((stream_name, source_url))
        if self.error:
            raise self.error
        return f"http://zlm:82/live/preview-{stream_name}.live.flv"

    def release(self, stream_name):
        self.released.append(stream_name)

    def stop_stream(self, stream_name):
        self.stopped.append(stream_name)


class FakeRemoteResponse:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    def read(self, _size):
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        self.closed = True


def camera(status="RUNNING", source_url=SOURCE_URL):
    now = datetime.now(timezone.utc)
    return main.CameraResponse(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Camera 1",
        sourceUrl=source_url,
        streamApp="live",
        streamName="camera-1",
        status=status,
        playbackUrl="/live/camera-1.live.flv",
        createdAt=now,
        updatedAt=now,
    )


@pytest.fixture(autouse=True)
def isolate_camera_store():
    original = dict(main.cameras)
    main.cameras.clear()
    yield
    main.cameras.clear()
    main.cameras.update(original)


async def collect_async_body(iterator):
    chunks = []
    async for chunk in iterator:
        chunks.append(chunk)
    return b"".join(chunks)


def test_live_proxy_acquires_derived_h264_relay_and_releases_after_stream(monkeypatch):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager()
    remote = FakeRemoteResponse([b"FLV\x01", b"payload"])
    opened_urls = []
    offloaded_calls = []

    async def fake_to_thread(function, *args):
        offloaded_calls.append((function, args))
        return function(*args)

    monkeypatch.setattr(main, "preview_relay_manager", manager, raising=False)
    monkeypatch.setattr(main, "asyncio", asyncio, raising=False)
    monkeypatch.setattr(main.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        main,
        "open_preview_remote",
        lambda url: opened_urls.append(url) or remote,
        raising=False,
    )

    response = main.proxy_flv_stream("camera-1")

    assert manager.acquired == [("camera-1", SOURCE_URL)]
    assert opened_urls == ["http://zlm:82/live/preview-camera-1.live.flv"]
    assert asyncio.run(collect_async_body(response.body_iterator)) == b"FLV\x01payload"
    assert offloaded_calls == [
        (remote.read, (64 * 1024,)),
        (remote.read, (64 * 1024,)),
        (remote.read, (64 * 1024,)),
    ]
    assert manager.released == ["camera-1"]
    assert remote.closed is True


def test_unknown_preview_stream_returns_404(monkeypatch):
    monkeypatch.setattr(main, "preview_relay_manager", FakePreviewManager(), raising=False)

    with pytest.raises(HTTPException) as raised:
        main.proxy_flv_stream("missing")

    assert raised.value.status_code == 404


def test_stopped_preview_stream_returns_409(monkeypatch):
    configured = camera(status="STOPPED")
    main.cameras[configured.id] = configured
    monkeypatch.setattr(main, "preview_relay_manager", FakePreviewManager(), raising=False)

    with pytest.raises(HTTPException) as raised:
        main.proxy_flv_stream("camera-1")

    assert raised.value.status_code == 409


def test_non_rtsp_preview_stream_returns_400(monkeypatch):
    configured = camera(source_url="http://camera.example/live.m3u8")
    main.cameras[configured.id] = configured
    monkeypatch.setattr(main, "preview_relay_manager", FakePreviewManager(), raising=False)

    with pytest.raises(HTTPException) as raised:
        main.proxy_flv_stream("camera-1")

    assert raised.value.status_code == 400


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (PreviewRelayError("failed"), 502),
        (PreviewRelayTimeout("timed out"), 504),
    ],
)
def test_preview_relay_failures_map_to_gateway_errors(monkeypatch, error, status_code):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager(error=error)
    monkeypatch.setattr(main, "preview_relay_manager", manager, raising=False)

    with pytest.raises(HTTPException) as raised:
        main.proxy_flv_stream("camera-1")

    assert raised.value.status_code == status_code
    assert SOURCE_URL not in str(raised.value.detail)


def test_upstream_open_failure_releases_acquired_relay(monkeypatch):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager()
    monkeypatch.setattr(main, "preview_relay_manager", manager, raising=False)

    def fail_open(_url):
        raise HTTPException(status_code=502, detail="upstream unavailable")

    monkeypatch.setattr(main, "open_preview_remote", fail_open, raising=False)

    with pytest.raises(HTTPException):
        main.proxy_flv_stream("camera-1")

    assert manager.stopped == ["camera-1"]


def test_preview_open_retries_404_until_derived_stream_is_ready(monkeypatch):
    remote = FakeRemoteResponse([b"FLV\x01"])
    attempts = []

    def open_after_publish(url):
        attempts.append(url)
        if len(attempts) < 3:
            raise HTTPException(status_code=404, detail="not published yet")
        return remote

    monkeypatch.setattr(main, "open_remote", open_after_publish)
    monkeypatch.setattr(main.time, "sleep", lambda _seconds: None)

    response = main.open_preview_remote("http://zlm/live/preview-camera-1.live.flv")

    assert response is remote
    assert len(attempts) == 3


def test_stopping_camera_stops_preview_relay(monkeypatch):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager()
    monkeypatch.setattr(main, "preview_relay_manager", manager)
    monkeypatch.setattr(main, "stop_worker_stream", lambda _camera_id: None)
    monkeypatch.setattr(main, "remove_zlmediakit_proxy", lambda _stream_name: None)
    monkeypatch.setattr(main, "persist_cameras", lambda: None)

    stopped = main.stop_camera(configured.id)

    assert stopped.status == "STOPPED"
    assert manager.stopped == ["camera-1"]


def test_deleting_camera_stops_preview_relay(monkeypatch):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager()
    monkeypatch.setattr(main, "preview_relay_manager", manager)
    monkeypatch.setattr(main, "stop_worker_stream", lambda _camera_id: None)
    monkeypatch.setattr(main, "remove_zlmediakit_proxy", lambda _stream_name: None)
    monkeypatch.setattr(main, "persist_cameras", lambda: None)

    main.delete_camera(configured.id)

    assert manager.stopped == ["camera-1"]


def test_updating_camera_source_stops_old_preview_relay(monkeypatch):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager()
    monkeypatch.setattr(main, "preview_relay_manager", manager)
    monkeypatch.setattr(main, "persist_cameras", lambda: None)

    updated = main.update_camera(
        configured.id,
        main.CameraUpdateRequest(
            sourceUrl="rtsp://admin:password@10.10.0.94/Streaming/Channels/101"
        ),
    )

    assert updated.sourceUrl != configured.sourceUrl
    assert manager.stopped == ["camera-1"]


def test_updating_camera_metadata_keeps_active_preview_relay(monkeypatch):
    configured = camera()
    main.cameras[configured.id] = configured
    manager = FakePreviewManager()
    monkeypatch.setattr(main, "preview_relay_manager", manager)
    monkeypatch.setattr(main, "persist_cameras", lambda: None)

    main.update_camera(
        configured.id,
        main.CameraUpdateRequest(description="updated"),
    )

    assert manager.stopped == []
