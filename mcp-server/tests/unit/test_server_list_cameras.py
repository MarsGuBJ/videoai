import asyncio
from datetime import datetime, timezone

import app.server as server
from app.models import Camera


def make_camera(**overrides) -> Camera:
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    data = {
        "id": "cam-1",
        "name": "园区摄像头",
        "sourceUrl": "rtsp://camera/live",
        "streamApp": "live",
        "streamName": "cam-1",
        "status": "RUNNING",
        "playbackUrl": "/live/cam-1.live.flv",
        "createdAt": now,
        "updatedAt": now,
        "nvrId": "main-nvr",
        "nvrChannel": "101",
        "nvrTrackId": "101",
        "nvrStreamType": "main",
    }
    data.update(overrides)
    return Camera(**data)


def test_list_cameras_returns_live_url_and_keeps_legacy_field(monkeypatch):
    async def fake_list_cameras():
        return [
            make_camera(),
            make_camera(
                id="nvr-only",
                name="录像通道",
                sourceUrl="",
                streamName="",
                playbackUrl="",
                nvrChannel="601",
                nvrTrackId="601",
            ),
        ]

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr("app.tools.cameras._public_url", lambda url: f"https://video.example{url}")

    result = asyncio.run(server.list_cameras())

    assert len(result["data"]) == 1
    item = result["data"][0]
    assert item["cameraId"] == "cam-1"
    assert item["url"] == "https://video.example/live/cam-1.live.flv"
    assert item["livePlaybackUrl"] == item["url"]
    assert item["nvrBinding"]["bound"] is True
    assert "录像通道" not in result["xml"]
    assert 'url="https://video.example/live/cam-1.live.flv"' in result["xml"]
    assert 'livePlaybackUrl="https://video.example/live/cam-1.live.flv"' in result["xml"]
