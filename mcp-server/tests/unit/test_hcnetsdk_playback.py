import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace

from app.hcnetsdk_playback import (
    HcNetSdkLibrary,
    HcNetSdkPlaybackProxy,
    PlaybackSession,
    channels_from_device_info,
    device_channel_numbers,
)


class FakeFfmpeg:
    def poll(self):
        return None


@dataclass
class FakeSession:
    stream_name: str
    playback_url: str
    recording_id: str = ""
    failed: str = ""
    ffmpeg: FakeFfmpeg = field(default_factory=FakeFfmpeg)
    expires_at: float = field(default_factory=lambda: time.monotonic() + 1800)
    speed: float = 1.0


def make_proxy() -> HcNetSdkPlaybackProxy:
    return HcNetSdkPlaybackProxy(
        host="192.168.11.198",
        port=8000,
        username="admin",
        password="cisdi123",
        channel=1,
        zlm_http_url="http://zlm",
        zlm_public_http_url="http://zlm",
        zlm_secret="secret",
        zlm_rtmp_push_base="rtmp://zlm/live",
        ttl_seconds=1800,
    )


def test_device_channel_numbers_combines_analog_and_digital_channels():
    assert device_channel_numbers(
        start_channel=1,
        analog_count=2,
        start_digital_channel=33,
        digital_count=2,
    ) == [1, 2, 33, 34]


def test_device_channel_numbers_deduplicates_overlapping_ranges():
    assert device_channel_numbers(
        start_channel=1,
        analog_count=1,
        start_digital_channel=1,
        digital_count=1,
    ) == [1]


def test_channels_from_device_info_combines_high_digital_channel_count():
    device = SimpleNamespace(
        struDeviceV30=SimpleNamespace(
            byStartChan=1,
            byChanNum=1,
            byStartDChan=33,
            byIPChanNum=2,
            byHighDChanNum=1,
        )
    )

    channels = channels_from_device_info(device)

    assert channels[0] == 1
    assert channels[1] == 33
    assert len(channels) == 259


def test_login_with_device_info_returns_user_and_channels():
    class FakeSdk:
        @staticmethod
        def NET_DVR_Login_V40(_login_info, device_info):
            info = device_info._obj.struDeviceV30
            info.byStartChan = 1
            info.byChanNum = 2
            return 7

    library = object.__new__(HcNetSdkLibrary)
    library.sdk = FakeSdk()

    session = library.login_with_device_info("10.10.0.1", 8000, "admin", "secret")

    assert session.user_id == 7
    assert session.channels == (1, 2)


def test_start_playback_keeps_one_existing_live_session(monkeypatch):
    proxy = make_proxy()
    proxy._sessions = {"old-1": FakeSession("old-1", "http://zlm/live/old-1.live.flv")}
    calls = []

    async def fake_cleanup():
        calls.append("cleanup")

    def fake_stop_session(session):
        calls.append(("stop", session.stream_name))

    def fake_start_session(recording, speed=1.0):
        calls.append(("start", recording.recordingId, speed))
        return FakeSession("new-1", "http://zlm/live/new-1.live.flv")

    monkeypatch.setattr(proxy, "_cleanup_expired_locked", fake_cleanup)
    monkeypatch.setattr(proxy, "_stop_session", fake_stop_session)
    monkeypatch.setattr(proxy, "_start_session", fake_start_session)

    recording = proxy.build_recording(
        datetime(2026, 7, 16, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 16, 9, 10, tzinfo=timezone.utc),
    )
    url = asyncio.run(proxy.start_playback(recording))

    assert url == "http://zlm/live/new-1.live.flv"
    assert "old-1" in proxy._sessions
    assert "new-1" in proxy._sessions
    assert calls == ["cleanup", ("start", recording.recordingId, 1.0)]


def test_start_playback_evicts_only_oldest_session_when_at_limit(monkeypatch):
    proxy = make_proxy()
    proxy._sessions = {
        "old-1": FakeSession("old-1", "http://zlm/live/old-1.live.flv"),
        "old-2": FakeSession("old-2", "http://zlm/live/old-2.live.flv"),
    }
    calls = []

    async def fake_cleanup():
        calls.append("cleanup")

    def fake_stop_session(session):
        calls.append(("stop", session.stream_name))

    def fake_start_session(recording, speed=1.0):
        calls.append(("start", recording.recordingId, speed))
        return FakeSession("new-1", "http://zlm/live/new-1.live.flv", recording_id=recording.recordingId)

    monkeypatch.setattr(proxy, "_cleanup_expired_locked", fake_cleanup)
    monkeypatch.setattr(proxy, "_stop_session", fake_stop_session)
    monkeypatch.setattr(proxy, "_start_session", fake_start_session)

    recording = proxy.build_recording(
        datetime(2026, 7, 16, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 16, 9, 10, tzinfo=timezone.utc),
    )
    url = asyncio.run(proxy.start_playback(recording))

    assert url == "http://zlm/live/new-1.live.flv"
    # 仅逐出最早建立的 old-1,old-2 继续播放
    assert list(proxy._sessions) == ["old-2", "new-1"]
    assert calls == [
        "cleanup",
        ("stop", "old-1"),
        ("start", recording.recordingId, 1.0),
    ]


def make_playback_session(speed: float = 1.0) -> PlaybackSession:
    return PlaybackSession(
        sdk=None,
        stream_name="hcn-test",
        host="10.10.7.253",
        port=8000,
        username="admin",
        password="secret",
        channel=2,
        start_time=datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 9, 8, 11, 0, tzinfo=timezone.utc),
        rtmp_url="rtmp://zlm/live/hcn-test",
        playback_url="http://zlm/live/hcn-test.live.flv",
        timeout=15,
        expires_at=time.monotonic() + 1800,
        speed=speed,
    )


def test_ffmpeg_args_default_speed_is_realtime():
    args = make_playback_session()._ffmpeg_args()

    assert "-re" in args
    assert "-readrate" not in args
    assert "-vf" not in args
    assert "-skip_frame" not in args


def test_ffmpeg_args_fast_speed_limits_readrate_and_retimestamps():
    args = make_playback_session(speed=8.0)._ffmpeg_args()

    assert "-re" not in args
    assert args[args.index("-readrate") + 1] == "8"
    assert args[args.index("-vf") + 1] == "setpts=PTS/8,fps=25"
    assert "-skip_frame" not in args


def test_ffmpeg_args_speed_16_decodes_keyframes_only():
    args = make_playback_session(speed=16.0)._ffmpeg_args()

    assert args[args.index("-skip_frame") + 1] == "nokey"
    assert args[args.index("-readrate") + 1] == "16"
    assert args.index("-skip_frame") < args.index("-i")


def test_ffmpeg_args_slow_motion_stretches_timestamps():
    args = make_playback_session(speed=0.5)._ffmpeg_args()

    assert args[args.index("-readrate") + 1] == "0.5"
    assert args[args.index("-vf") + 1] == "setpts=PTS/0.5,fps=25"


def test_speed_change_restarts_session_with_new_speed(monkeypatch):
    """同一段录像倍速变化时停掉旧会话并以新倍速起流。"""
    proxy = make_proxy()
    proxy._sessions = {
        "old-1": FakeSession("old-1", "http://zlm/live/old-1.live.flv", recording_id="rec-1"),
    }
    calls = []

    async def fake_cleanup():
        pass

    def fake_stop_session(session):
        calls.append(("stop", session.stream_name))

    def fake_start_session(recording, speed=1.0):
        calls.append(("start", recording.recordingId, speed))
        return FakeSession(
            "new-1", "http://zlm/live/new-1.live.flv", recording_id=recording.recordingId, speed=speed
        )

    monkeypatch.setattr(proxy, "_cleanup_expired_locked", fake_cleanup)
    monkeypatch.setattr(proxy, "_stop_session", fake_stop_session)
    monkeypatch.setattr(proxy, "_start_session", fake_start_session)

    recording = proxy.build_recording(
        datetime(2026, 7, 16, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 16, 9, 10, tzinfo=timezone.utc),
    )
    recording.recordingId = "rec-1"
    url = asyncio.run(proxy.start_playback(recording, 4.0))

    assert url == "http://zlm/live/new-1.live.flv"
    assert calls == [("stop", "old-1"), ("start", "rec-1", 4.0)]
    assert "old-1" not in proxy._sessions
