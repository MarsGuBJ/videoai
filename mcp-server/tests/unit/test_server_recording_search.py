import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import quote

import pytest

import app.server as server
from app.hcnetsdk_playback import build_hcnetsdk_download_recording
from app.models import RecordingSegment
from app.server import (
    attach_first_playable_recording_stream,
    normalize_recording_limit,
    parse_datetime,
    parse_recording_tracks,
    per_track_recording_limit,
)


def test_resolve_recording_tracks_defaults_to_601(monkeypatch):
    async def fail_list_record_tracks():
        raise AssertionError("default recording track should not query NVR track list")

    monkeypatch.setattr(server.hikvision, "list_record_tracks", fail_list_record_tracks)

    assert asyncio.run(server.resolve_recording_tracks("")) == ["601"]


def test_parse_recording_tracks_accepts_requested_channel_list():
    assert parse_recording_tracks("602,603") == ["602", "603"]


def test_parse_recording_tracks_allows_any_nvr_channel_and_deduplicates():
    assert parse_recording_tracks("101, 604,101，158") == ["101", "604", "158"]


def test_normalize_recording_limit_allows_larger_all_channel_results():
    assert normalize_recording_limit(500) == 200


def test_per_track_recording_limit_distributes_total_limit_across_tracks():
    assert per_track_recording_limit(50, 3) == 17


def test_parse_datetime_converts_aware_input_to_beijing_time():
    parsed = parse_datetime("2026-02-17T00:00:00Z")

    assert parsed.utcoffset() == timedelta(hours=8)
    assert parsed.hour == 8


def test_parse_datetime_treats_naive_input_as_beijing_time():
    parsed = parse_datetime("2026-02-17T08:00:00")

    assert parsed.utcoffset() == timedelta(hours=8)
    assert parsed.hour == 8


def test_attach_first_playable_recording_stream_tries_next_track(monkeypatch):
    start = datetime(2026, 7, 7, 0, 0, 0, tzinfo=timezone.utc)
    recordings = [
        RecordingSegment(
            recordingId="rec-101",
            cameraId="cam-101",
            cameraName="NVR-101",
            trackId="101",
            startTime=start,
            endTime=start,
            playbackUri="rtsp://nvr/Streaming/tracks/101",
        ),
        RecordingSegment(
            recordingId="rec-601",
            cameraId="cam-601",
            cameraName="NVR-601",
            trackId="601",
            startTime=start,
            endTime=start,
            playbackUri="rtsp://nvr/Streaming/tracks/601",
        ),
    ]
    items = [server.recording_item(recording) for recording in recordings]
    failed_tracks = {}

    async def fake_start_rtsp_relay(uid, rtsp_url, output_format, overlay_text="", fallback_file=""):
        if uid == "rec-101":
            raise RuntimeError("not playable")
        return "http://zlm/live/rec-601.live.flv"

    monkeypatch.setattr(server.media_proxy, "start_rtsp_relay", fake_start_rtsp_relay)

    asyncio.run(attach_first_playable_recording_stream(items, recordings, "flv", failed_tracks))

    assert items[0].get("url") is None
    assert items[1]["url"] == "http://zlm/live/rec-601.live.flv"
    assert "streamUrl" not in items[1]
    assert items[1]["format"] == "flv"
    assert "101" in failed_tracks


def test_search_recordings_returns_dynamic_link_without_starting_stream(monkeypatch):
    """autoProxy=True 时返回按需建流的动态链接，搜索本身不创建 SDK 回放会话。"""
    start = datetime(2026, 7, 7, 0, 0, 0, tzinfo=timezone.utc)

    async def fail_start_playback(recording, speed=1.0):
        raise AssertionError("search_recordings must not start a playback stream")

    monkeypatch.setattr(server.hcnetsdk_playback, "start_playback", fail_start_playback)
    monkeypatch.setattr(server.hcnetsdk_playback, "ensure_playback", fail_start_playback)
    monkeypatch.setattr(
        "app.tools.recordings.settings", SimpleNamespace(mcp_public_base_url="http://mcp.test:8097")
    )

    result = asyncio.run(
        server.search_recordings(
            startTime=start.isoformat(),
            endTime=start.replace(minute=10).isoformat(),
            limit=10,
            trackId="601,701",
            autoProxy=True,
        )
    )

    assert result["searchedTrackIds"] == ["1"]
    assert len(result["data"]) == 1
    assert result["data"][0]["trackId"] == "1"
    assert result["data"][0]["format"] == "flv"
    assert result["data"][0]["source"] == "hikvision_hcnetsdk_playback"
    assert result["failedTrackIds"] == {}
    link_start = parse_datetime(start.isoformat())
    link_end = parse_datetime(start.replace(minute=10).isoformat())
    expected_url = (
        "http://mcp.test:8097/recording-live"
        f"?startTime={quote(link_start.isoformat())}&endTime={quote(link_end.isoformat())}"
    )
    assert result["data"][0]["url"] == expected_url
    assert "streamUrl" not in result["data"][0]
    assert "/recording-live?startTime=" in result["xml"]
    assert "&amp;endTime=" in result["xml"]
    assert "streamUrl" not in result["xml"]


@pytest.mark.parametrize("nvr", ["10.10.7.252", "10.10.7.253"])
def test_download_recording_routes_to_selected_nvr_and_cleans_temp_file(monkeypatch, tmp_path, nvr):
    start = datetime(2026, 7, 7, 0, 0, 0, tzinfo=timezone.utc)
    temp_mp4 = tmp_path / "download.mp4"
    temp_mp4.write_bytes(b"mp4")
    calls = []

    class FakeDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            return build_hcnetsdk_download_recording(nvr, 8000, channel or self.channel, start_time, end_time)

        async def measure_clock_skew(self):
            return 0.0

        async def download_mp4(self, recording):
            calls.append(("download", recording.metadata["deviceHost"], recording.trackId))
            return temp_mp4

    def fake_upload_mp4(source_file, object_name):
        calls.append(("upload", source_file.name, object_name))
        return f"http://minio/public/{object_name}"

    monkeypatch.setattr("app.tools.recordings.hcnetsdk_downloaders", {nvr: FakeDownloader()})
    monkeypatch.setattr(server.recording_mp4_storage, "upload_mp4", fake_upload_mp4)

    result = asyncio.run(
        server.download_recording(
            nvr=nvr,
            startTime=start.isoformat(),
            endTime=start.replace(minute=10).isoformat(),
        )
    )

    assert calls[0][0] == "download"
    assert calls[0][1] == nvr
    assert calls[0][2] == "1"
    assert calls[1][0] == "upload"
    assert calls[1][2].startswith(f"recordings/{nvr}/ch1/")
    assert calls[1][2].endswith(".mp4")
    assert result["searchedTrackIds"] == ["1"]
    assert result["data"][0]["format"] == "mp4"
    assert result["data"][0]["source"] == "hikvision_hcnetsdk_download"
    assert result["data"][0]["metadata"]["deviceHost"] == nvr
    assert result["data"][0]["url"].startswith("http://minio/public/recordings/")
    assert 'format="mp4"' not in result["xml"]
    assert result["failedTrackIds"] == {}
    assert not temp_mp4.exists()


def test_download_recording_rejects_unknown_nvr():
    with pytest.raises(ValueError, match="nvr must be one of: 10.10.7.252, 10.10.7.253"):
        asyncio.run(
            server.download_recording(
                nvr="10.10.7.254",
                startTime="2026-07-07T00:00:00+00:00",
                endTime="2026-07-07T00:10:00+00:00",
            )
        )


def test_download_recording_derives_channel_from_track_id_and_compensates_skew(monkeypatch, tmp_path):
    """trackId 201 换算为 SDK 通道 2；测得的时钟偏差叠加到 SDK 下载时间段，展示时间保持请求值。"""
    temp_mp4 = tmp_path / "download.mp4"
    temp_mp4.write_bytes(b"mp4")
    calls = {}

    class FakeDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time, channel=None):
            calls["sdk_start"] = start_time
            calls["channel"] = channel or self.channel
            return build_hcnetsdk_download_recording("10.10.7.252", 8000, channel or self.channel, start_time, end_time)

        async def measure_clock_skew(self):
            return -3600.0

        async def download_mp4(self, recording):
            calls["download_start"] = recording.startTime
            return temp_mp4

    monkeypatch.setattr("app.tools.recordings.hcnetsdk_downloaders", {"10.10.7.252": FakeDownloader()})
    monkeypatch.setattr(server.recording_mp4_storage, "upload_mp4", lambda source_file, object_name: "http://minio/x.mp4")

    start = datetime(2026, 8, 31, 9, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    result = asyncio.run(
        server.download_recording(
            nvr="10.10.7.252",
            startTime=start.isoformat(),
            endTime=start.replace(minute=2).isoformat(),
            trackId="201",
        )
    )

    assert calls["channel"] == 2
    assert calls["sdk_start"] == start - timedelta(hours=1)
    # 传给 SDK 下载的 recording 必须保留补偿后的时间，不能回退成请求时间
    assert calls["download_start"] == start - timedelta(hours=1)
    assert result["data"][0]["trackId"] == "2"
    assert result["data"][0]["startTime"] == start.isoformat()
