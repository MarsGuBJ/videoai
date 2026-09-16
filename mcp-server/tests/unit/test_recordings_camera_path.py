"""recordings 工具的 cameraId（多 NVR）路径单元测试。"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import quote

import pytest

import app.server as server
from app.hcnetsdk_playback import NET_DVR_PLAYBACK_BY_TIME, build_hcnetsdk_download_recording, build_hcnetsdk_recording
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
        assert item["id"] == "cam-1"
        assert item["cameraId"] == "cam-1"
        assert item["cameraName"] == "园区东门"
        assert item["source"] == "hikvision_hcnetsdk_playback"
        assert "username" not in item["metadata"]
        assert item["metadata"]["deviceHost"] == "10.10.8.10"
        # 段已入缓存，供录像资源查询使用
        assert server.recording_cache.get(segment.recordingId) is not None
    assert "cameraId=cam-1" in result["xml"]
    assert 'id="cam-1"' in result["xml"]


class FakeSingletonPlayback:
    """无 cameraId 路径使用的单例回放代理替身（host/channel 供摄像头反查）。"""

    host = "10.10.8.10"
    channel = 1

    def build_recording(self, start_time, end_time):
        return build_hcnetsdk_recording(self.host, 8000, self.channel, start_time, end_time)


def test_search_recordings_without_camera_id_resolves_camera_uuid(monkeypatch):
    """无 cameraId 路径：按 NVR 主机+通道反查平台摄像头，id/cameraId 返回摄像头 UUID。"""
    camera = make_nvr_camera()

    async def fake_list_cameras():
        return [camera]

    monkeypatch.setattr("app.tools.recordings.hcnetsdk_playback", FakeSingletonPlayback())
    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr(
        "app.tools.recordings.settings", SimpleNamespace(mcp_public_base_url="http://mcp.test:8097")
    )

    result = asyncio.run(
        server.search_recordings(
            startTime="2026-09-01T09:00:00",
            endTime="2026-09-01T10:00:00",
            limit=10,
        )
    )

    item = result["data"][0]
    assert item["id"] == "cam-1"
    assert item["cameraId"] == "cam-1"
    assert item["cameraName"] == "园区东门"
    assert 'id="cam-1"' in result["xml"]


def test_search_recordings_without_camera_id_keeps_synthetic_id_when_no_camera_matches(monkeypatch):
    """无 cameraId 路径：平台列表无匹配摄像头时保留合成的设备通道标识。"""

    async def fake_list_cameras():
        return [make_nvr_camera(nvrChannel="2", nvrTrackId="201")]

    monkeypatch.setattr("app.tools.recordings.hcnetsdk_playback", FakeSingletonPlayback())
    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr(
        "app.tools.recordings.settings", SimpleNamespace(mcp_public_base_url="http://mcp.test:8097")
    )

    result = asyncio.run(
        server.search_recordings(
            startTime="2026-09-01T09:00:00",
            endTime="2026-09-01T10:00:00",
            limit=10,
        )
    )

    item = result["data"][0]
    assert item["id"] == "10.10.8.10-channel-1"
    assert item["cameraId"] == "10.10.8.10-channel-1"


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

        async def download_mp4(self, recording, speedx=1):
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
