import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

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
        "onlineStatus": "ONLINE",
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
    monkeypatch.setattr(
        "app.tools.cameras.settings",
        SimpleNamespace(
            videoai_media_public_base_url="https://video.example",
            zlm_public_http_url="https://video.example",
            videoai_base_url="https://video.example",
        ),
    )


def test_list_cameras_returns_id_url_name_and_excludes_nvr_only(monkeypatch):
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
    # status 取自设备在线状态（onlineStatus），不再取拉流状态
    # url 为后端按需拉流代理地址，播放时自动开播
    assert item == {
        "id": "cam-1",
        "status": "RUNNING",
        "url": "https://video.example/api/live/cam-1.live.flv",
        "name": "园区摄像头",
    }
    assert "录像通道" not in result["xml"]
    assert 'id="cam-1"' in result["xml"]
    assert 'url="https://video.example/api/live/cam-1.live.flv"' in result["xml"]
    assert 'status="RUNNING"' in result["xml"]


def test_list_cameras_non_zlm_sources_keep_passthrough_url(monkeypatch):
    install_fake_cameras(
        monkeypatch,
        [
            make_camera(id="cam-http", sourceUrl="http://camera/live", playbackUrl="http://camera/live.flv"),
            make_camera(
                id="cam-mjpeg",
                sourceUrl="http://camera/mjpeg",
                playbackUrl="/api/streams/live/cam-mjpeg.mjpeg",
            ),
        ],
    )
    monkeypatch.setattr("app.tools.cameras._public_url", lambda url: url)

    result = asyncio.run(server.list_cameras())

    urls = {item["id"]: item["url"] for item in result["data"]}
    assert urls == {
        "cam-http": "http://camera/live.flv",
        "cam-mjpeg": "/api/streams/live/cam-mjpeg.mjpeg",
    }


def test_list_cameras_status_reflects_online_status(monkeypatch):
    install_fake_cameras(
        monkeypatch,
        [
            make_camera(id="cam-online", streamName="cam-online", onlineStatus="ONLINE"),
            make_camera(id="cam-offline", streamName="cam-offline", onlineStatus="OFFLINE"),
            make_camera(id="cam-unknown", streamName="cam-unknown", onlineStatus="UNKNOWN"),
            make_camera(id="cam-missing", streamName="cam-missing", onlineStatus=None),
            # 拉流状态为 STOPPED 但设备在线时，status 仍应为 RUNNING
            make_camera(id="cam-stopped", streamName="cam-stopped", status="STOPPED", onlineStatus="ONLINE"),
        ],
    )

    result = asyncio.run(server.list_cameras())

    statuses = {item["id"]: item["status"] for item in result["data"]}
    assert statuses == {
        "cam-online": "RUNNING",
        "cam-offline": "STOPPED",
        "cam-unknown": "STOPPED",
        "cam-missing": "STOPPED",
        "cam-stopped": "RUNNING",
    }
    assert 'id="cam-offline"' in result["xml"]
    assert 'status="STOPPED"' in result["xml"]


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
