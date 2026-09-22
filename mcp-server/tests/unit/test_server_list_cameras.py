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


def install_fake_cameras(monkeypatch, cameras):
    async def fake_list_cameras():
        return cameras

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr("app.tools.cameras._public_url", lambda url: f"https://video.example{url}")


def test_list_cameras_returns_id_status_url_name_and_excludes_nvr_only(monkeypatch):
    install_fake_cameras(
        monkeypatch,
        [
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
        ],
    )

    result = asyncio.run(server.list_cameras())

    assert result["total"] == 1
    assert result["page"] == 1
    assert len(result["data"]) == 1
    item = result["data"][0]
    assert item == {
        "id": "cam-1",
        "status": "RUNNING",
        "url": "https://video.example/live/cam-1.live.flv",
        "name": "园区摄像头",
    }
    assert "录像通道" not in result["xml"]
    assert 'id="cam-1"' in result["xml"]
    assert 'url="https://video.example/live/cam-1.live.flv"' in result["xml"]


def test_list_cameras_filters_by_name_fuzzy_case_insensitive(monkeypatch):
    install_fake_cameras(
        monkeypatch,
        [
            make_camera(id="cam-1", name="园区东门"),
            make_camera(id="cam-2", name="园区西门", streamName="cam-2"),
            make_camera(id="cam-3", name="Office Gate", streamName="cam-3"),
        ],
    )

    result = asyncio.run(server.list_cameras(name="东门"))
    assert [item["id"] for item in result["data"]] == ["cam-1"]
    assert result["total"] == 1

    result = asyncio.run(server.list_cameras(name="office"))
    assert [item["id"] for item in result["data"]] == ["cam-3"]

    result = asyncio.run(server.list_cameras(name=""))
    assert result["total"] == 3


def test_list_cameras_paginates(monkeypatch):
    cameras = [make_camera(id=f"cam-{i}", name=f"摄像头{i}", streamName=f"cam-{i}") for i in range(1, 6)]
    install_fake_cameras(monkeypatch, cameras)

    page1 = asyncio.run(server.list_cameras(page=1, pageSize=2))
    assert [item["id"] for item in page1["data"]] == ["cam-1", "cam-2"]
    assert page1["total"] == 5
    assert page1["page"] == 1
    assert page1["pageSize"] == 2

    page3 = asyncio.run(server.list_cameras(page=3, pageSize=2))
    assert [item["id"] for item in page3["data"]] == ["cam-5"]

    beyond = asyncio.run(server.list_cameras(page=4, pageSize=2))
    assert beyond["data"] == []
    assert beyond["total"] == 5


def test_list_cameras_pagination_applies_after_name_filter(monkeypatch):
    cameras = [make_camera(id=f"east-{i}", name=f"东门{i}", streamName=f"east-{i}") for i in range(1, 4)]
    cameras.append(make_camera(id="west-1", name="西门1", streamName="west-1"))
    install_fake_cameras(monkeypatch, cameras)

    result = asyncio.run(server.list_cameras(name="东门", page=2, pageSize=2))

    assert result["total"] == 3
    assert [item["id"] for item in result["data"]] == ["east-3"]
