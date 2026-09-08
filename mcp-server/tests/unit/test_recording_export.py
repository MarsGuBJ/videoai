"""NVR 录像导出（RTSP 回放抓流 → MP4 → MinIO）的单元测试。"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import app.recording_export as export
from app.recording_export import (
    MAX_EXPORT_DURATION_SECONDS,
    RecordingExportError,
    build_track_playback_url,
    export_recording_mp4,
    is_valid_mp4,
    to_nvr_wall_digits,
)

BJT = timezone(timedelta(hours=8))


def fake_settings(**overrides):
    values = {
        "hikvision_base_url": "http://192.168.11.251",
        "hikvision_username": "admin",
        "hikvision_password": "p@ss&word",
        "request_timeout_seconds": 15,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_to_nvr_wall_digits_applies_skew_and_z_suffix():
    value = datetime(2026, 8, 31, 10, 0, 0, tzinfo=BJT)
    assert to_nvr_wall_digits(value, 0) == "20260831T100000Z"
    assert to_nvr_wall_digits(value, -3600) == "20260831T090000Z"


def test_to_nvr_wall_digits_rejects_naive_datetime():
    with pytest.raises(ValueError, match="timezone-aware"):
        to_nvr_wall_digits(datetime(2026, 8, 31, 10, 0, 0), 0)


def test_build_track_playback_url_uses_tracks_path_with_trailing_slash(monkeypatch):
    monkeypatch.setattr(export, "settings", fake_settings())
    url = build_track_playback_url(
        "201",
        datetime(2026, 8, 31, 10, 0, 0, tzinfo=BJT),
        datetime(2026, 8, 31, 10, 2, 0, tzinfo=BJT),
        0,
    )
    assert "/Streaming/tracks/201/?starttime=20260831T100000Z&endtime=20260831T100200Z" in url
    assert "admin:p%40ss%26word@192.168.11.251:554" in url


def test_build_track_playback_url_requires_nvr_config(monkeypatch):
    monkeypatch.setattr(export, "settings", fake_settings(hikvision_base_url=""))
    start = datetime(2026, 8, 31, 10, 0, tzinfo=BJT)
    with pytest.raises(RecordingExportError, match="HIKVISION_NVR_BASE_URL"):
        build_track_playback_url("201", start, start + timedelta(minutes=1), 0)


def test_export_recording_mp4_happy_path(monkeypatch, tmp_path):
    captured = {}
    mp4 = tmp_path / "capture.mp4"
    mp4.write_bytes(b"mp4")

    async def fake_skew():
        return -3600.0

    def fake_capture(url, duration):
        captured["url"] = url
        captured["duration"] = duration
        return mp4

    def fake_upload(source_file, object_name):
        captured["object_name"] = object_name
        return f"http://minio/public/{object_name}"

    monkeypatch.setattr(export, "settings", fake_settings())
    monkeypatch.setattr(export, "fetch_nvr_clock_skew", fake_skew)
    monkeypatch.setattr(export, "capture_playback_to_mp4", fake_capture)
    monkeypatch.setattr(export.recording_mp4_storage, "upload_mp4", fake_upload)

    result = asyncio.run(
        export_recording_mp4(
            "201",
            datetime(2026, 8, 31, 10, 0, 0, tzinfo=BJT),
            datetime(2026, 8, 31, 10, 2, 0, tzinfo=BJT),
        )
    )

    assert captured["duration"] == 120
    assert "starttime=20260831T090000Z" in captured["url"]
    assert captured["object_name"].startswith("recordings/exports/201/")
    assert result["videoUrl"].startswith("http://minio/public/recordings/exports/201/")
    assert result["durationSeconds"] == 120
    assert result["trackId"] == "201"
    assert result["nvrClockSkewSeconds"] == -3600
    assert not mp4.exists()


def test_export_recording_mp4_rejects_excessive_duration(monkeypatch):
    monkeypatch.setattr(export, "settings", fake_settings())
    with pytest.raises(ValueError, match="must not exceed"):
        asyncio.run(
            export_recording_mp4(
                "201",
                datetime(2026, 8, 31, 10, 0, 0, tzinfo=BJT),
                datetime(2026, 8, 31, 10, 0, 0, tzinfo=BJT) + timedelta(seconds=MAX_EXPORT_DURATION_SECONDS + 1),
            )
        )


def test_export_recording_mp4_rejects_inverted_range(monkeypatch):
    monkeypatch.setattr(export, "settings", fake_settings())
    with pytest.raises(ValueError, match="later than"):
        asyncio.run(
            export_recording_mp4(
                "201",
                datetime(2026, 8, 31, 10, 2, 0, tzinfo=BJT),
                datetime(2026, 8, 31, 10, 0, 0, tzinfo=BJT),
            )
        )


def test_is_valid_mp4_rejects_tiny_file(tmp_path):
    tiny = tmp_path / "tiny.mp4"
    tiny.write_bytes(b"x" * 1024)
    assert not is_valid_mp4(tiny)
    assert not is_valid_mp4(tmp_path / "missing.mp4")


def test_fetch_nvr_clock_skew_returns_zero_without_base_url(monkeypatch):
    monkeypatch.setattr(export, "settings", fake_settings(hikvision_base_url=""))
    assert asyncio.run(export.fetch_nvr_clock_skew()) == 0.0


def test_capture_tolerates_stalled_stream_with_partial_content(monkeypatch, tmp_path):
    """NVR 停发导致抓流超时时，用已抓到的 TS 继续 remux 出 MP4。"""
    import json
    import subprocess

    monkeypatch.setattr(export.tempfile, "mkdtemp", lambda prefix: str(tmp_path))

    def fake_run(cmd, **kwargs):
        if "mpegts" in cmd:
            (tmp_path / "capture.ts").write_bytes(b"x" * (200 * 1024))
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
        if "+faststart" in cmd:
            (tmp_path / "export.mp4").write_bytes(b"y" * (200 * 1024))
            return subprocess.CompletedProcess(cmd, 0, "", "")
        # ffprobe
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"format": {"duration": "63.0"}}), "")

    monkeypatch.setattr(export.subprocess, "run", fake_run)

    result = export.capture_playback_to_mp4("rtsp://example", 60)
    assert result.name.startswith("recording-export-")
    assert result.suffix == ".mp4"
    result.unlink(missing_ok=True)


def test_capture_rejects_empty_recording(monkeypatch, tmp_path):
    """抓流超时且没有有效内容时报"该时段无可用录像"。"""
    import subprocess

    monkeypatch.setattr(export.tempfile, "mkdtemp", lambda prefix: str(tmp_path))

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

    monkeypatch.setattr(export.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="无可用录像"):
        export.capture_playback_to_mp4("rtsp://example", 60)


def test_export_recording_prefers_sdk_download(monkeypatch, tmp_path):
    """SDK 下载为默认导出方式：成功时不尝试 RTSP 抓流。"""
    import app.tools.recordings as recordings_tools
    from app.hcnetsdk_playback import build_hcnetsdk_download_recording

    mp4 = tmp_path / "sdk.mp4"
    mp4.write_bytes(b"mp4")
    calls = {}

    async def fail_rtsp(track_id, start, end):
        raise AssertionError("RTSP capture must not be attempted when SDK download succeeds")

    class FakeDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            calls["channel"] = channel
            calls["sdk_start"] = start_time
            return build_hcnetsdk_download_recording(
                "192.168.11.251", 8000, channel or self.channel, start_time, end_time
            )

        async def measure_clock_skew(self):
            return -3600.0

        async def download_mp4(self, recording):
            return mp4

    monkeypatch.setattr(export, "settings", fake_settings())
    monkeypatch.setattr(export, "hcnetsdk_downloaders", {"192.168.11.251": FakeDownloader()})
    monkeypatch.setattr(
        export.recording_mp4_storage, "upload_mp4", lambda source_file, object_name: f"http://minio/public/{object_name}"
    )
    monkeypatch.setattr(recordings_tools, "export_recording_mp4", fail_rtsp)

    result = asyncio.run(
        recordings_tools.export_recording(
            trackId="201",
            startTime="2026-08-31T10:00:00",
            endTime="2026-08-31T10:02:00",
        )
    )

    assert calls["channel"] == 2
    assert calls["sdk_start"] == datetime(2026, 8, 31, 9, 0, 0, tzinfo=BJT)
    data = result["data"]
    assert data["exportMethod"] == "hcnetsdk_download"
    assert data["videoUrl"].startswith("http://minio/public/recordings/exports/201/")
    assert data["startTime"] == "2026-08-31T10:00:00+08:00"
    assert data["durationSeconds"] == 120
    assert not mp4.exists()


def test_export_recording_falls_back_to_rtsp_capture(monkeypatch, tmp_path):
    """SDK 下载失败（或无下载器）时，回退到 RTSP 回放抓流。"""
    import app.tools.recordings as recordings_tools
    from app.hcnetsdk_playback import build_hcnetsdk_download_recording

    mp4 = tmp_path / "rtsp.mp4"
    mp4.write_bytes(b"mp4")

    class FailingDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            return build_hcnetsdk_download_recording(
                "192.168.11.251", 8000, channel or self.channel, start_time, end_time
            )

        async def measure_clock_skew(self):
            return 0.0

        async def download_mp4(self, recording):
            raise RuntimeError("sdk boom")

    async def fake_rtsp_export(track_id, start, end):
        return {
            "videoUrl": "http://minio/public/recordings/exports/201/rtsp.mp4",
            "durationSeconds": 120,
            "trackId": track_id,
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "nvrClockSkewSeconds": 0,
            "exportElapsedSeconds": 121.0,
        }

    monkeypatch.setattr(export, "settings", fake_settings())
    monkeypatch.setattr(export, "hcnetsdk_downloaders", {"192.168.11.251": FailingDownloader()})
    monkeypatch.setattr(recordings_tools, "export_recording_mp4", fake_rtsp_export)

    result = asyncio.run(
        recordings_tools.export_recording(
            trackId="201",
            startTime="2026-08-31T10:00:00",
            endTime="2026-08-31T10:02:00",
        )
    )

    assert result["data"]["videoUrl"].endswith("rtsp.mp4")
    assert result["data"]["durationSeconds"] == 120


def test_export_recording_reports_both_errors_when_all_fail(monkeypatch):
    """SDK 下载与 RTSP 抓流都失败时，错误信息同时包含两侧原因。"""
    import app.tools.recordings as recordings_tools
    from app.hcnetsdk_playback import build_hcnetsdk_download_recording

    class FailingDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            return build_hcnetsdk_download_recording(
                "192.168.11.251", 8000, channel or self.channel, start_time, end_time
            )

        async def measure_clock_skew(self):
            return 0.0

        async def download_mp4(self, recording):
            raise RuntimeError("sdk boom")

    async def fake_rtsp_export(track_id, start, end):
        raise RecordingExportError("ffmpeg capture failed: 453 Not Enough Bandwidth")

    monkeypatch.setattr(export, "settings", fake_settings())
    monkeypatch.setattr(export, "hcnetsdk_downloaders", {"192.168.11.251": FailingDownloader()})
    monkeypatch.setattr(recordings_tools, "export_recording_mp4", fake_rtsp_export)

    with pytest.raises(RecordingExportError, match=r"sdk download failed.*rtsp export failed"):
        asyncio.run(
            recordings_tools.export_recording(
                trackId="201",
                startTime="2026-08-31T10:00:00",
                endTime="2026-08-31T10:02:00",
            )
        )


def test_export_recording_long_range_goes_straight_to_sdk_download(monkeypatch, tmp_path):
    """超过 RTSP 20 分钟上限的时段直接走 SDK 下载，不尝试抓流。"""
    import app.tools.recordings as recordings_tools
    from app.hcnetsdk_playback import build_hcnetsdk_download_recording

    mp4 = tmp_path / "sdk.mp4"
    mp4.write_bytes(b"mp4")
    calls = {}

    async def fail_rtsp(track_id, start, end):
        raise AssertionError("long ranges must not attempt RTSP capture")

    class FakeDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            calls["channel"] = channel
            return build_hcnetsdk_download_recording(
                "192.168.11.251", 8000, channel or self.channel, start_time, end_time
            )

        async def measure_clock_skew(self):
            return 0.0

        async def download_mp4(self, recording):
            return mp4

    monkeypatch.setattr(export, "settings", fake_settings())
    monkeypatch.setattr(export, "hcnetsdk_downloaders", {"192.168.11.251": FakeDownloader()})
    monkeypatch.setattr(
        export.recording_mp4_storage, "upload_mp4", lambda source_file, object_name: f"http://minio/public/{object_name}"
    )
    monkeypatch.setattr(recordings_tools, "export_recording_mp4", fail_rtsp)

    result = asyncio.run(
        recordings_tools.export_recording(
            trackId="601",
            startTime="2026-09-02T07:00:00",
            endTime="2026-09-02T08:00:00",
        )
    )

    assert result["data"]["exportMethod"] == "hcnetsdk_download"
    assert result["data"]["durationSeconds"] == 3600
    assert calls["channel"] == 6


def test_export_recording_long_range_sdk_failure_propagates(monkeypatch):
    """长时段 SDK 下载失败时直接抛错，不尝试 RTSP 抓流（RTSP 有 20 分钟上限）。"""
    import app.tools.recordings as recordings_tools
    from app.hcnetsdk_playback import build_hcnetsdk_download_recording

    class FailingDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            return build_hcnetsdk_download_recording(
                "192.168.11.251", 8000, channel or self.channel, start_time, end_time
            )

        async def measure_clock_skew(self):
            return 0.0

        async def download_mp4(self, recording):
            raise RuntimeError("sdk boom")

    async def fail_rtsp(track_id, start, end):
        raise AssertionError("long ranges must not fall back to RTSP capture")

    monkeypatch.setattr(export, "settings", fake_settings())
    monkeypatch.setattr(export, "hcnetsdk_downloaders", {"192.168.11.251": FailingDownloader()})
    monkeypatch.setattr(recordings_tools, "export_recording_mp4", fail_rtsp)

    with pytest.raises(RecordingExportError, match="sdk download failed"):
        asyncio.run(
            recordings_tools.export_recording(
                trackId="601",
                startTime="2026-09-02T07:00:00",
                endTime="2026-09-02T08:00:00",
            )
        )


def test_export_recording_with_camera_id_uses_camera_device(monkeypatch, tmp_path):
    """传 cameraId 时按摄像头 sourceUrl 凭据的设备做 SDK 下载，不走白名单 NVR。"""
    import app.tools.recordings as recordings_tools
    from app.hcnetsdk_playback import build_hcnetsdk_download_recording

    mp4 = tmp_path / "camera.mp4"
    mp4.write_bytes(b"mp4")
    calls = {}

    class FakeDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            calls["channel"] = channel
            return build_hcnetsdk_download_recording(
                "10.10.1.20", 8000, channel or self.channel, start_time, end_time
            )

        async def measure_clock_skew(self):
            return 0.0

        async def download_mp4(self, recording):
            return mp4

    async def fake_get_camera(camera_id):
        calls["camera_id"] = camera_id
        return SimpleNamespace(id=camera_id)

    async def fake_resolve_credentials(camera, lookup, known_hosts):
        return SimpleNamespace(track_id="101", channel=1)

    monkeypatch.setattr(recordings_tools.videoai, "get_camera", fake_get_camera)
    monkeypatch.setattr(recordings_tools, "resolve_device_credentials", fake_resolve_credentials)
    monkeypatch.setattr(
        recordings_tools, "nvr_devices", SimpleNamespace(proxy_for_credentials=lambda credentials: FakeDownloader())
    )
    monkeypatch.setattr(
        export.recording_mp4_storage, "upload_mp4", lambda source_file, object_name: f"http://minio/public/{object_name}"
    )

    result = asyncio.run(
        recordings_tools.export_recording(
            cameraId="cam-1",
            startTime="2026-09-04T10:00:00",
            endTime="2026-09-04T10:02:00",
        )
    )

    assert calls["camera_id"] == "cam-1"
    assert calls["channel"] == 1
    data = result["data"]
    assert data["exportMethod"] == "hcnetsdk_download"
    assert data["trackId"] == "101"
    assert data["videoUrl"].startswith("http://minio/public/recordings/exports/101/")
    assert not mp4.exists()


def test_export_recording_rejects_range_beyond_sdk_limit():
    """超过 SDK 下载 2 小时上限时报错。"""
    import app.tools.recordings as recordings_tools

    with pytest.raises(ValueError, match="7200"):
        asyncio.run(
            recordings_tools.export_recording(
                trackId="601",
                startTime="2026-09-02T06:00:00",
                endTime="2026-09-02T09:00:00",
            )
        )
