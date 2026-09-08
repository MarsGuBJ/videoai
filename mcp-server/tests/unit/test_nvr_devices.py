"""nvr_devices 单元测试：凭据解析、per-device 代理注册表与 ISAPI 录像检索映射。"""

import asyncio
import threading
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.models import Camera
from app.nvr_devices import (
    DeviceCredentials,
    NvrDeviceError,
    NvrDeviceRegistry,
    parse_device_credentials,
    search_segments,
)

BJT = timezone(timedelta(hours=8))


def make_camera(**overrides) -> Camera:
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


def make_registry() -> NvrDeviceRegistry:
    return NvrDeviceRegistry("http://zlm", "http://zlm-public", "secret", "rtmp://zlm/live", 1800, 5)


def test_parse_device_credentials_extracts_url_credentials_and_channel():
    credentials = parse_device_credentials(make_camera())

    assert credentials.host == "10.10.8.10"
    assert credentials.username == "admin"
    assert credentials.password == "p@ss"
    assert credentials.channel == 1
    assert credentials.track_id == "101"
    assert credentials.sdk_port == 8000


def test_parse_device_credentials_derives_channel_from_track_id():
    credentials = parse_device_credentials(make_camera(nvrChannel=None, nvrTrackId="201"))

    assert credentials.channel == 2
    assert credentials.track_id == "201"


def test_parse_device_credentials_allows_sdk_port_override(monkeypatch):
    assert parse_device_credentials(make_camera(), sdk_port=9000).sdk_port == 9000

    monkeypatch.setenv("HCNETSDK_DEVICE_PORT", "9001")
    assert parse_device_credentials(make_camera()).sdk_port == 9001


def test_parse_device_credentials_rejects_unbound_camera():
    with pytest.raises(ValueError, match="nvrTrackId/nvrChannel"):
        parse_device_credentials(make_camera(nvrChannel=None, nvrTrackId=None))


def test_parse_device_credentials_rejects_missing_source_url():
    with pytest.raises(ValueError, match="no sourceUrl"):
        parse_device_credentials(make_camera(sourceUrl=""))


def test_parse_device_credentials_rejects_url_without_credentials():
    with pytest.raises(ValueError, match="host/username/password"):
        parse_device_credentials(make_camera(sourceUrl="rtsp://10.10.8.10:554/Streaming/Channels/101"))


def test_registry_caches_proxy_per_host():
    registry = make_registry()
    camera = make_camera()

    proxy = registry.proxy_for(camera)

    assert proxy.host == "10.10.8.10"
    assert proxy.port == 8000
    assert proxy.channel == 1
    assert registry.proxy_for(camera) is proxy
    # 同一 NVR 上的另一路摄像头复用同一代理实例
    assert registry.proxy_for(make_camera(id="cam-2", nvrChannel="2", nvrTrackId="201")) is proxy
    assert registry.proxy_for(make_camera(sourceUrl="rtsp://admin:p%40ss@10.10.8.11:554/x")) is not proxy


def test_registry_proxy_for_is_thread_safe():
    registry = make_registry()
    camera = make_camera()
    barrier = threading.Barrier(8)
    proxies = []

    def worker():
        barrier.wait()
        proxies.append(registry.proxy_for(camera))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len({id(proxy) for proxy in proxies}) == 1


SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<CMSearchResult xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <matchList>
    <searchMatchItem>
      <trackID>101</trackID>
      <timeSpan>
        <startTime>2026-09-01T01:00:00Z</startTime>
        <endTime>2026-09-01T01:10:00Z</endTime>
      </timeSpan>
      <mediaSegmentDescriptor>
        <playbackURI>rtsp://10.10.8.10/Streaming/tracks/101/?starttime=20260901T010000Z</playbackURI>
      </mediaSegmentDescriptor>
    </searchMatchItem>
  </matchList>
</CMSearchResult>"""


class FakeResponse:
    def __init__(self, text: str = SEARCH_XML, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


def install_fake_httpx(monkeypatch, response=None, error=None):
    calls = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            calls["auth"] = kwargs.get("auth")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, content=None, headers=None):
            calls["url"] = url
            calls["body"] = content
            if error is not None:
                raise error
            return response or FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return calls


def test_search_segments_maps_matches_to_sdk_playback_segments(monkeypatch):
    calls = install_fake_httpx(monkeypatch)
    start = datetime(2026, 9, 1, 9, 0, tzinfo=BJT)
    end = datetime(2026, 9, 1, 10, 0, tzinfo=BJT)

    segments = asyncio.run(search_segments(make_camera(), start, end, 10))

    assert calls["url"] == "http://10.10.8.10/ISAPI/ContentMgmt/search"
    assert "<trackID>101</trackID>" in calls["body"]
    assert len(segments) == 1
    segment = segments[0]
    assert segment.cameraId == "cam-1"
    assert segment.cameraName == "园区东门"
    assert segment.trackId == "101"
    assert segment.source == "hikvision_hcnetsdk_playback"
    assert segment.startTime == datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
    assert segment.metadata["deviceHost"] == "10.10.8.10"
    assert segment.metadata["devicePort"] == 8000
    assert segment.metadata["channel"] == 1
    assert "password" not in segment.metadata
    assert "p@ss" not in str(segment.metadata)
    # recordingId 确定性生成：同样的输入得到同样的 ID
    again = asyncio.run(search_segments(make_camera(), start, end, 10))
    assert again[0].recordingId == segment.recordingId
    assert len(segment.recordingId) == 32


SEARCH_START = datetime(2026, 9, 1, tzinfo=BJT)
SEARCH_END = datetime(2026, 9, 1, 1, tzinfo=BJT)


def test_search_segments_returns_empty_list_when_device_has_no_recordings(monkeypatch):
    empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <CMSearchResult xmlns="http://www.hikvision.com/ver20/XMLSchema"><matchList/></CMSearchResult>"""
    install_fake_httpx(monkeypatch, response=FakeResponse(empty_xml))

    assert asyncio.run(search_segments(make_camera(), SEARCH_START, SEARCH_END)) == []


def test_search_segments_raises_when_device_unreachable(monkeypatch):
    install_fake_httpx(monkeypatch, error=httpx.ConnectError("boom"))

    with pytest.raises(NvrDeviceError, match="unreachable") as exc_info:
        asyncio.run(search_segments(make_camera(), SEARCH_START, SEARCH_END))
    assert "p@ss" not in str(exc_info.value)


def test_search_segments_raises_on_auth_failure(monkeypatch):
    install_fake_httpx(monkeypatch, response=FakeResponse("Unauthorized", status_code=401))

    with pytest.raises(NvrDeviceError, match="HTTP 401") as exc_info:
        asyncio.run(search_segments(make_camera(), SEARCH_START, SEARCH_END))
    assert "p@ss" not in str(exc_info.value)


def test_segment_metadata_never_contains_password():
    credentials = DeviceCredentials("10.10.8.10", "admin", "top-secret", 1, "101")
    from app.nvr_devices import parse_segment_matches

    segments = parse_segment_matches(SEARCH_XML, make_camera(), credentials, 10)

    assert segments
    assert "top-secret" not in repr(segments[0].metadata)
