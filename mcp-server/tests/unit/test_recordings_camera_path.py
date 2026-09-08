"""recordings 工具的 cameraId（多 NVR）路径单元测试。"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import quote

import pytest

import app.server as server
from app.hcnetsdk_playback import NET_DVR_PLAYBACK_BY_TIME, build_hcnetsdk_download_recording
from app.models import Camera, RecordingSegment

BJT = timezone(timedelta(hours=8))


def make_nvr_camera(**overrides) -> Camera:
    now = datetime(2026, 9, 1, tzinfo=BJT)
    data = {
        "id": "cam-1",
        "name": "园区东门",
        "sourceUrl": "rtsp://admin:p%40ss@10.10.8.10:554/Streaming/Channels/101",
        "streamApp": "live",
        "streamName": "cam-1",
        "status": "RUNNING",
        "playbackUrl": "/live/cam-1.live.flv",
        "createdAt": now,
        "updatedAt": now,
        "nvrId": "10.10.8.10",
        "nvrChannel": "1",
        "nvrTrackId": "101",
        "nvrStreamType": "main",
    }
    data.update(overrides)
    return Camera(**data)


def make_segment(camera: Camera, start: datetime, minutes: int = 10) -> RecordingSegment:
    return RecordingSegment(
        recordingId=f"rec-{camera.id}-{start.isoformat()}",
        cameraId=camera.id,
        cameraName=camera.name,
        trackId="101",
        startTime=start,
        endTime=start + timedelta(minutes=minutes),
        playbackUri="hcnetsdk://10.10.8.10:8000/channels/1",
        source=NET_DVR_PLAYBACK_BY_TIME,
        metadata={
            "deviceHost": "10.10.8.10",
            "devicePort": 8000,
            "channel": 1,
            "username": "admin",
            "protocol": "HCNetSDK",
            "sdkApi": "NET_DVR_PlayBackByTime_V40",
        },
    )


def install_camera_lookup(monkeypatch, camera):
    async def fake_get_camera(camera_id):
        assert camera_id == camera.id
        return camera

    monkeypatch.setattr(server.videoai, "get_camera", fake_get_camera)


@pytest.fixture(autouse=True)
def no_channel_lookup(monkeypatch):
    """默认不做 IPC→NVR 反查（避免测试触网）；反查场景由用例自行替换。"""
    monkeypatch.setattr("app.tools.recordings.channel_lookup", None)


def test_search_recordings_with_camera_id_returns_segment_links(monkeypatch):
    """cameraId 路径：ISAPI 检索结果入缓存，autoProxy 链接带 cameraId 与段自身起止时间。"""
    camera = make_nvr_camera()
    start = datetime(2026, 9, 1, 9, 0, tzinfo=BJT)
    segments = [make_segment(camera, start), make_segment(camera, start + timedelta(minutes=10))]
    searched = {}

    install_camera_lookup(monkeypatch, camera)

    async def fake_search_segments(cam, start_time, end_time, limit, timeout=15, credentials=None):
        searched["camera"] = cam
        searched["range"] = (start_time, end_time)
        return segments

    monkeypatch.setattr("app.tools.recordings.search_segments", fake_search_segments)
    monkeypatch.setattr(
        "app.tools.recordings.settings",
        SimpleNamespace(mcp_public_base_url="http://mcp.test:8097", request_timeout_seconds=15),
    )

    result = asyncio.run(
        server.search_recordings(
            cameraId="cam-1",
            startTime="2026-09-01T09:00:00",
            endTime="2026-09-01T10:00:00",
            limit=10,
        )
    )

    assert searched["camera"] is camera
    assert len(result["data"]) == 2
    assert result["failedTrackIds"] == {}
    assert result["searchedTrackIds"] == ["101", "101"]
    for segment, item in zip(segments, result["data"], strict=True):
        expected_url = (
            "http://mcp.test:8097/recording-live?cameraId=cam-1"
            f"&startTime={quote(segment.startTime.isoformat())}&endTime={quote(segment.endTime.isoformat())}"
        )
        assert item["url"] == expected_url
        assert item["format"] == "flv"
        assert item["cameraId"] == "cam-1"
        assert item["cameraName"] == "园区东门"
        assert item["source"] == "hikvision_hcnetsdk_playback"
        assert "username" not in item["metadata"]
        assert item["metadata"]["deviceHost"] == "10.10.8.10"
        # 段已入缓存，可供 get_recording_stream 使用
        assert server.recording_cache.get(segment.recordingId) is not None
    assert "cameraId=cam-1" in result["xml"]


def test_search_recordings_with_camera_id_returns_empty_when_device_has_no_recordings(monkeypatch):
    camera = make_nvr_camera()
    install_camera_lookup(monkeypatch, camera)

    async def fake_search_segments(cam, start_time, end_time, limit, timeout=15, credentials=None):
        return []

    monkeypatch.setattr("app.tools.recordings.search_segments", fake_search_segments)

    result = asyncio.run(
        server.search_recordings(
            cameraId="cam-1",
            startTime="2026-09-01T09:00:00",
            endTime="2026-09-01T10:00:00",
        )
    )

    assert result["data"] == []
    assert result["searchedTrackIds"] == ["101"]
    assert result["failedTrackIds"] == {}


def test_search_recordings_with_camera_id_rejects_unbound_camera(monkeypatch):
    camera = make_nvr_camera(nvrChannel=None, nvrTrackId=None)
    install_camera_lookup(monkeypatch, camera)

    async def fail_search_segments(*args, **kwargs):
        raise AssertionError("unbound camera must not trigger an ISAPI search")

    monkeypatch.setattr("app.tools.recordings.search_segments", fail_search_segments)

    with pytest.raises(ValueError, match="nvrTrackId/nvrChannel"):
        asyncio.run(
            server.search_recordings(
                cameraId="cam-1",
                startTime="2026-09-01T09:00:00",
                endTime="2026-09-01T10:00:00",
            )
        )


def test_get_recording_stream_routes_camera_recording_to_per_device_proxy(monkeypatch):
    """metadata.deviceHost 非单例设备时按 recording.cameraId 查摄像头并路由到 per-device 代理。"""
    camera = make_nvr_camera()
    start = datetime(2026, 9, 1, 9, 0, tzinfo=BJT)
    recording = make_segment(camera, start)
    server.recording_cache.put_many([recording])
    install_camera_lookup(monkeypatch, camera)
    calls = {}

    class FakeProxy:
        async def start_playback(self, rec, speed=1.0):
            calls["recording"] = rec
            return "http://zlm/live/hcn-per-device.live.flv"

    class FakeRegistry:
        def proxy_for_credentials(self, credentials):
            calls["credentials"] = credentials
            return FakeProxy()

    monkeypatch.setattr("app.tools.recordings.nvr_devices", FakeRegistry())

    async def fail_start_playback(rec, speed=1.0):
        raise AssertionError("camera recording must not use the singleton playback proxy")

    monkeypatch.setattr(server.hcnetsdk_playback, "start_playback", fail_start_playback)

    result = asyncio.run(server.get_recording_stream(recording.recordingId))

    assert result["url"] == "http://zlm/live/hcn-per-device.live.flv"
    assert result["format"] == "flv"
    assert calls["credentials"].host == "10.10.8.10"
    assert calls["credentials"].channel == 1
    assert calls["recording"].recordingId == recording.recordingId
    assert "username" not in result["metadata"]


def test_get_recording_stream_keeps_singleton_for_legacy_recording(monkeypatch):
    """metadata.deviceHost 为空或等于单例设备时不查摄像头，仍走单例 hcnetsdk_playback。"""
    start = datetime(2026, 9, 1, 9, 0, tzinfo=BJT)
    recording = RecordingSegment(
        recordingId="rec-legacy",
        cameraId="192.168.11.198-channel-1",
        cameraName="IPC-198",
        trackId="1",
        startTime=start,
        endTime=start + timedelta(minutes=5),
        playbackUri="hcnetsdk://192.168.11.198:8000/channels/1",
        source=NET_DVR_PLAYBACK_BY_TIME,
        metadata={"deviceHost": "192.168.11.198", "devicePort": 8000, "channel": 1},
    )
    server.recording_cache.put_many([recording])

    async def fail_get_camera(camera_id):
        raise AssertionError("legacy recording must not query the camera API")

    async def fake_start_playback(rec, speed=1.0):
        return "http://zlm/live/hcn-legacy.live.flv"

    monkeypatch.setattr(server.videoai, "get_camera", fail_get_camera)
    monkeypatch.setattr(server.hcnetsdk_playback, "start_playback", fake_start_playback)

    result = asyncio.run(server.get_recording_stream("rec-legacy"))

    assert result["url"] == "http://zlm/live/hcn-legacy.live.flv"


def test_download_recording_with_camera_id_uses_per_device_proxy(monkeypatch, tmp_path):
    """cameraId 路径：registry 取设备代理，时钟偏差补偿到 SDK 下载时间，展示时间保持请求值。"""
    camera = make_nvr_camera()
    install_camera_lookup(monkeypatch, camera)
    temp_mp4 = tmp_path / "download.mp4"
    temp_mp4.write_bytes(b"mp4")
    calls = {}

    class FakeProxy:
        def build_download_recording(self, start_time, end_time, channel=None):
            calls["sdk_start"] = start_time
            calls["channel"] = channel
            return build_hcnetsdk_download_recording("10.10.8.10", 8000, channel or 1, start_time, end_time)

        async def measure_clock_skew(self):
            return -3600.0

        async def download_mp4(self, recording):
            calls["download_start"] = recording.startTime
            return temp_mp4

    class FakeRegistry:
        def proxy_for_credentials(self, credentials):
            calls["credentials"] = credentials
            return FakeProxy()

    monkeypatch.setattr("app.tools.recordings.nvr_devices", FakeRegistry())
    monkeypatch.setattr(
        server.recording_mp4_storage, "upload_mp4", lambda source_file, object_name: f"http://minio/{object_name}"
    )

    start = datetime(2026, 9, 1, 9, 0, tzinfo=BJT)
    result = asyncio.run(
        server.download_recording(
            nvr="",
            cameraId="cam-1",
            startTime=start.isoformat(),
            endTime=start.replace(minute=2).isoformat(),
        )
    )

    assert calls["credentials"].host == "10.10.8.10"
    assert calls["credentials"].channel == 1
    assert calls["channel"] == 1
    assert calls["sdk_start"] == start - timedelta(hours=1)
    assert calls["download_start"] == start - timedelta(hours=1)
    item = result["data"][0]
    assert item["cameraId"] == "cam-1"
    assert item["cameraName"] == "园区东门"
    assert item["startTime"] == start.isoformat()
    assert item["format"] == "mp4"
    assert item["url"].startswith("http://minio/recordings/10.10.8.10/ch1/")
    assert item["metadata"]["deviceHost"] == "10.10.8.10"
    assert result["failedTrackIds"] == {}
    assert not temp_mp4.exists()


def test_download_recording_without_nvr_and_camera_id_keeps_existing_error():
    with pytest.raises(ValueError, match="nvr must be one of"):
        asyncio.run(
            server.download_recording(
                nvr="",
                startTime="2026-09-01T09:00:00",
                endTime="2026-09-01T09:05:00",
            )
        )


def test_get_recording_stream_rejects_unsupported_speed():
    """倍速不在 NVR 实测支持档位（0.25~32）时直接报错，不起流。"""
    with pytest.raises(ValueError, match="unsupported playback speed"):
        asyncio.run(server.get_recording_stream("rec-any", speed=3.0))


def test_get_recording_stream_passes_speed_to_playback_proxy(monkeypatch):
    """倍速透传到 SDK 回放代理的 start_playback。"""
    camera = make_nvr_camera()
    start = datetime(2026, 9, 1, 9, 0, tzinfo=BJT)
    recording = make_segment(camera, start)
    server.recording_cache.put_many([recording])
    install_camera_lookup(monkeypatch, camera)
    calls = {}

    class FakeProxy:
        async def start_playback(self, rec, speed=1.0):
            calls["speed"] = speed
            return "http://zlm/live/hcn-speed.live.flv"

    class FakeRegistry:
        def proxy_for_credentials(self, credentials):
            return FakeProxy()

    monkeypatch.setattr("app.tools.recordings.nvr_devices", FakeRegistry())

    result = asyncio.run(server.get_recording_stream(recording.recordingId, speed=8.0))

    assert result["url"] == "http://zlm/live/hcn-speed.live.flv"
    assert calls["speed"] == 8.0
