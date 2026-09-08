"""HcNetSdkPlaybackProxy 会话复用与最老逐出策略的单元测试。"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.hcnetsdk_playback import HcNetSdkError, HcNetSdkPlaybackProxy, build_hcnetsdk_recording

BJT = timezone(timedelta(hours=8))


def make_proxy() -> HcNetSdkPlaybackProxy:
    return HcNetSdkPlaybackProxy(
        "10.0.0.1",
        8000,
        "u",
        "p",
        1,
        "http://zlm",
        "http://zlm-public",
        "secret",
        "rtmp://zlm/live",
        1800,
        5,
    )


def make_recording(offset_minutes: int = 0):
    start = datetime(2026, 9, 2, 8, 0, tzinfo=BJT) + timedelta(minutes=offset_minutes)
    return build_hcnetsdk_recording("10.0.0.1", 8000, 1, start, start + timedelta(minutes=5))


class FakeFfmpeg:
    def poll(self):
        return None


def make_session(stream_name: str, recording_id: str):
    return SimpleNamespace(
        stream_name=stream_name,
        recording_id=recording_id,
        playback_url=f"http://zlm-public/live/{stream_name}.live.flv",
        failed="",
        ffmpeg=FakeFfmpeg(),
        expires_at=time.monotonic() + 1800,
        speed=1.0,
    )


def test_ensure_playback_reuses_live_session(monkeypatch):
    """同一 recordingId 已有健康会话时直接复用，不新建 NVR 会话。"""
    proxy = make_proxy()
    recording = make_recording()
    session = make_session("hcn-a", recording.recordingId)
    proxy._sessions[session.stream_name] = session

    def fail_start(rec, speed=1.0):
        raise AssertionError("must reuse the existing session")

    monkeypatch.setattr(proxy, "_start_session", fail_start)

    url = asyncio.run(proxy.ensure_playback(recording))

    assert url == session.playback_url
    assert list(proxy._sessions) == [session.stream_name]


def test_ensure_playback_evicts_oldest_when_at_limit(monkeypatch):
    """达到并发上限时逐出最早建立的会话再建新流。"""
    proxy = make_proxy()
    proxy._max_live_sessions = 1
    old = make_session("hcn-old", "rec-old")
    proxy._sessions[old.stream_name] = old
    new_recording = make_recording(10)
    new_session = make_session("hcn-new", new_recording.recordingId)
    stopped = []

    monkeypatch.setattr(proxy, "_start_session", lambda rec, speed=1.0: new_session)
    monkeypatch.setattr(proxy, "_stop_session", lambda session: stopped.append(session.stream_name))

    url = asyncio.run(proxy.ensure_playback(new_recording))

    assert url == new_session.playback_url
    assert stopped == ["hcn-old"]
    assert list(proxy._sessions) == ["hcn-new"]


def test_ensure_playback_evicts_and_retries_on_start_failure(monkeypatch):
    """新建失败（如 NVR 会话数限制）时逐出最老会话并重试，直到成功。"""
    proxy = make_proxy()
    proxy._max_live_sessions = 5
    old = make_session("hcn-old", "rec-old")
    proxy._sessions[old.stream_name] = old
    recording = make_recording()
    new_session = make_session("hcn-new", recording.recordingId)
    stopped = []
    calls = []

    def flaky_start(rec, speed=1.0):
        calls.append(rec.recordingId)
        if len(calls) == 1:
            raise HcNetSdkError("NET_DVR_PlayBackByTime_V40 failed: 17")
        return new_session

    monkeypatch.setattr(proxy, "_start_session", flaky_start)
    monkeypatch.setattr(proxy, "_stop_session", lambda session: stopped.append(session.stream_name))

    url = asyncio.run(proxy.ensure_playback(recording))

    assert url == new_session.playback_url
    assert stopped == ["hcn-old"]
    assert len(calls) == 2
    assert list(proxy._sessions) == ["hcn-new"]


def test_ensure_playback_raises_after_all_sessions_evicted(monkeypatch):
    """逐出全部会话后仍失败时抛出最后一次错误。"""
    proxy = make_proxy()
    old = make_session("hcn-old", "rec-old")
    proxy._sessions[old.stream_name] = old
    stopped = []

    def always_fail(rec, speed=1.0):
        raise HcNetSdkError("NET_DVR_PlayBackByTime_V40 failed: 17")

    monkeypatch.setattr(proxy, "_start_session", always_fail)
    monkeypatch.setattr(proxy, "_stop_session", lambda session: stopped.append(session.stream_name))

    with pytest.raises(HcNetSdkError, match="17"):
        asyncio.run(proxy.ensure_playback(make_recording()))

    assert stopped == ["hcn-old"]
    assert not proxy._sessions
