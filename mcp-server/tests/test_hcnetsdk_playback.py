from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
from types import SimpleNamespace

from app.hcnetsdk_playback import (
    HcNetSdkLibrary,
    HcNetSdkPlaybackProxy,
    channels_from_device_info,
    device_channel_numbers,
)


@dataclass
class FakeSession:
    stream_name: str
    playback_url: str


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

    def fake_start_session(recording):
        calls.append(("start", recording.recordingId))
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
    assert calls == ["cleanup", ("start", recording.recordingId)]


def test_start_playback_stops_existing_live_sessions_when_two_are_active(monkeypatch):
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

    def fake_start_session(recording):
        calls.append(("start", recording.recordingId))
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
    assert list(proxy._sessions) == ["new-1"]
    assert calls == [
        "cleanup",
        ("stop", "old-1"),
        ("stop", "old-2"),
        ("start", recording.recordingId),
    ]
