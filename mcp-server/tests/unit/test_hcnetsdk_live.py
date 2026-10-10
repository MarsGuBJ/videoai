"""LivePullManager 单元测试。"""

import asyncio
from types import SimpleNamespace

import pytest

from app.hcnetsdk_live import LivePullManager


def make_manager() -> LivePullManager:
    return LivePullManager("http://zlm", "secret", "rtmp://zlm/live", 5)


def make_started_session(stream_name: str):
    return SimpleNamespace(stream_name=stream_name, failed="", real_handle=1, user_id=0)


class FakeSdkLibrary:
    @classmethod
    def instance(cls):
        return SimpleNamespace()


def test_ffmpeg_args_always_transcodes_to_h264() -> None:
    session = SimpleNamespace(rtmp_url="rtmp://zlm/live/cam-1")
    args = LivePullSession_args(session)  # type: ignore[arg-type]
    assert "libx264" in args
    assert "-f" in args and "flv" in args


def LivePullSession_args(session):  # noqa: N802  # 便捷构造：仅取 _ffmpeg_args 静态逻辑
    from app.hcnetsdk_live import LivePullSession

    return LivePullSession._ffmpeg_args(session)  # type: ignore[attr-defined]


def test_start_reuses_running_session(monkeypatch) -> None:
    manager = make_manager()
    monkeypatch.setattr("app.hcnetsdk_live.HcNetSdkLibrary", FakeSdkLibrary)
    session = make_started_session("cam-1")
    monkeypatch.setattr(
        "app.hcnetsdk_live.LivePullSession.start", lambda self: setattr(self, "real_handle", 1)
    )
    monkeypatch.setattr(manager, "_wait_until_stream_ready", lambda session: None)
    monkeypatch.setattr(manager, "_watch", lambda session: None)

    async def run() -> None:
        first = await manager.start("cam-1", "10.0.0.1", 8000, "u", "p")
        manager._sessions["cam-1"] = session
        second = await manager.start("cam-1", "10.0.0.1", 8000, "u", "p")
        assert second is session
        assert first.stream_name == "cam-1"

    asyncio.run(run())


def test_start_failure_cleans_up(monkeypatch) -> None:
    manager = make_manager()
    monkeypatch.setattr("app.hcnetsdk_live.HcNetSdkLibrary", FakeSdkLibrary)
    calls = {"stop": 0}

    def boom(self):
        raise RuntimeError("login failed")

    monkeypatch.setattr("app.hcnetsdk_live.LivePullSession.start", boom)
    monkeypatch.setattr("app.hcnetsdk_live.LivePullSession.stop", lambda self: calls.__setitem__("stop", calls["stop"] + 1))

    async def run() -> None:
        with pytest.raises(RuntimeError):
            await manager.start("cam-2", "10.0.0.2", 8000, "u", "p")
        assert "cam-2" not in manager._sessions
        assert calls["stop"] == 1

    asyncio.run(run())
