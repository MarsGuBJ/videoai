"""IPC → NVR 通道反查（NvrChannelLookup / resolve_device_credentials）单元测试。"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models import Camera
from app.nvr_devices import (
    DeviceCredentials,
    NvrChannelLookup,
    NvrDeviceRegistry,
    parse_input_proxy_channels,
    resolve_device_credentials,
    track_id_from_source_url,
)

BJT = timezone(timedelta(hours=8))

INPUT_PROXY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<InputProxyChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <InputProxyChannel>
    <id>189</id>
    <sourceInputPortDescriptor>
      <ipAddress>10.10.0.93</ipAddress>
    </sourceInputPortDescriptor>
  </InputProxyChannel>
  <InputProxyChannel>
    <id>195</id>
    <sourceInputPortDescriptor>
      <ipAddress>10.10.0.94</ipAddress>
    </sourceInputPortDescriptor>
  </InputProxyChannel>
</InputProxyChannelList>
"""


def make_ipc_camera(**overrides) -> Camera:
    """sourceUrl 直连 IPC（非 NVR）的摄像头；nvrTrackId 为批量导入的脏数据。"""
    now = datetime(2026, 9, 1, tzinfo=BJT)
    data = {
        "id": "cam-ipc-1",
        "name": "1号低压柔性线枪机02",
        "sourceUrl": "rtsp://admin:ipc-pass@10.10.0.93:554/Streaming/Channels/101",
        "streamApp": "live",
        "streamName": "cam-ipc-1",
        "status": "RUNNING",
        "playbackUrl": "/live/cam-ipc-1.live.flv",
        "createdAt": now,
        "updatedAt": now,
        "nvrId": None,
        "nvrChannel": None,
        "nvrTrackId": "101",
        "nvrStreamType": "main",
    }
    data.update(overrides)
    return Camera(**data)


def make_lookup(hosts=("10.10.7.252",), mapping=None, failing=(), device_credentials=None):
    """构造不触网的 NvrChannelLookup：failing 中的主机抛异常，其余返回 mapping。"""

    async def fake_fetch(self, host):
        if host in failing:
            raise ConnectionError("unreachable")
        return mapping or []

    lookup = NvrChannelLookup(
        hosts, "admin", "nvr-pass", timeout=1, ttl_seconds=600, device_credentials=device_credentials
    )
    lookup._fetch_channels = fake_fetch.__get__(lookup)
    return lookup


def test_parse_input_proxy_channels():
    channels = parse_input_proxy_channels(INPUT_PROXY_XML)

    assert channels == [(189, "10.10.0.93"), (195, "10.10.0.94")]


def test_lookup_hit_returns_nvr_host_and_channel():
    lookup = make_lookup(mapping=[(189, "10.10.0.93")])

    assert asyncio.run(lookup.lookup("10.10.0.93")) == ("10.10.7.252", 189)


def test_lookup_miss_returns_none():
    lookup = make_lookup(mapping=[(189, "10.10.0.93")])

    assert asyncio.run(lookup.lookup("10.10.9.9")) is None


def test_lookup_skips_unreachable_nvr():
    """单台 NVR 拉取失败不阻塞其余 NVR 的映射。"""
    lookup = make_lookup(hosts=("10.10.7.252", "10.10.7.253"))
    fetched = {}

    async def fake_fetch(self, host):
        if host == "10.10.7.252":
            raise ConnectionError("unreachable")
        fetched[host] = True
        return [(2, "10.10.2.21")]

    lookup._fetch_channels = fake_fetch.__get__(lookup)

    assert asyncio.run(lookup.lookup("10.10.2.21")) == ("10.10.7.253", 2)
    assert fetched == {"10.10.7.253": True}


def test_lookup_caches_within_ttl():
    lookup = make_lookup(mapping=[(189, "10.10.0.93")])
    fetches = 0

    original = lookup._fetch_all

    async def counting_fetch_all():
        nonlocal fetches
        fetches += 1
        return await original()

    lookup._fetch_all = counting_fetch_all

    asyncio.run(lookup.lookup("10.10.0.93"))
    asyncio.run(lookup.lookup("10.10.0.94"))

    assert fetches == 1


def test_resolve_credentials_for_nvr_camera_skips_lookup():
    """sourceUrl 指向已知 NVR 时不反查，沿用内嵌凭据与 nvrTrackId 换算通道。"""
    camera = make_ipc_camera(sourceUrl="rtsp://admin:nvr-pass@10.10.7.253:554/Streaming/Channels/201", nvrTrackId="201")

    async def fail_lookup(ipc_host):
        raise AssertionError("NVR camera must not trigger a channel lookup")

    lookup = SimpleNamespace(lookup=fail_lookup)
    credentials = asyncio.run(resolve_device_credentials(camera, lookup, {"10.10.7.253"}))

    assert credentials.host == "10.10.7.253"
    assert credentials.username == "admin"
    assert credentials.password == "nvr-pass"
    assert credentials.channel == 2
    assert credentials.track_id == "201"


def test_resolve_credentials_for_ipc_camera_uses_lookup():
    """sourceUrl 直连 IPC 时反查所属 NVR：用 NVR 凭据与实际通道号（忽略脏 nvrTrackId）。"""
    camera = make_ipc_camera()
    lookup = make_lookup(mapping=[(189, "10.10.0.93")])

    credentials = asyncio.run(resolve_device_credentials(camera, lookup, {"10.10.7.252"}))

    assert credentials.host == "10.10.7.252"
    assert credentials.username == "admin"
    assert credentials.password == "nvr-pass"
    assert credentials.channel == 189
    assert credentials.track_id == "18901"


def test_resolve_credentials_falls_back_on_lookup_miss():
    """反查未命中时回退原解析：直连 IPC 且 nvrTrackId 可换算时按 sourceUrl 主机处理。"""
    camera = make_ipc_camera()
    lookup = make_lookup(mapping=[])

    credentials = asyncio.run(resolve_device_credentials(camera, lookup, {"10.10.7.252"}))

    assert credentials.host == "10.10.0.93"
    assert credentials.channel == 1


def test_resolve_credentials_unbound_camera_still_raises():
    """反查未命中且摄像头未绑定 NVR 时照旧报 ValueError。"""
    camera = make_ipc_camera(nvrTrackId=None)
    lookup = make_lookup(mapping=[])

    with pytest.raises(ValueError, match="nvrTrackId/nvrChannel"):
        asyncio.run(resolve_device_credentials(camera, lookup, {"10.10.7.252"}))


def test_credentials_for_prefers_device_specific_credentials():
    """CVR 等凭据不同的设备按主机取专属凭据，未配置的主机回退默认凭据。"""
    lookup = make_lookup(device_credentials={"172.21.200.21": ("admin", "cvr-pass")})

    assert lookup.credentials_for("172.21.200.21") == ("admin", "cvr-pass")
    assert lookup.credentials_for("10.10.7.252") == ("admin", "nvr-pass")


def test_track_id_from_source_url():
    assert track_id_from_source_url("rtsp://admin:pass@172.21.200.21:554/Streaming/Channels/12801") == "12801"
    assert track_id_from_source_url("rtsp://admin:pass@10.10.7.252:554/Streaming/tracks/201") == "201"
    assert track_id_from_source_url("rtsp://admin:pass@10.10.0.93:554/h264/ch1/main/av_stream") == ""


def test_resolve_credentials_for_cvr_camera_derives_track_from_url():
    """sourceUrl 指向 CVR 且平台未填 trackId 时，从 URL 通道路径兜底（12801 → 通道 128）。"""
    camera = make_ipc_camera(
        sourceUrl="rtsp://admin:cvr-pass@172.21.200.21:554/Streaming/Channels/12801",
        nvrTrackId=None,
    )

    async def fail_lookup(ipc_host):
        raise AssertionError("CVR camera must not trigger a channel lookup")

    lookup = SimpleNamespace(lookup=fail_lookup)
    credentials = asyncio.run(resolve_device_credentials(camera, lookup, {"172.21.200.21"}))

    assert credentials.host == "172.21.200.21"
    assert credentials.channel == 128
    assert credentials.track_id == "12801"


def test_resolve_credentials_lookup_miss_error_notes_reverse_lookup():
    """反查未命中且未绑定 NVR 时，错误消息注明反查未命中便于定位。"""
    camera = make_ipc_camera(nvrTrackId=None)
    lookup = make_lookup(mapping=[])

    with pytest.raises(ValueError, match="reverse lookup missed"):
        asyncio.run(resolve_device_credentials(camera, lookup, {"10.10.7.252"}))


def test_resolve_credentials_uses_cvr_credentials_on_cvr_hit():
    """反查命中 CVR 时用 CVR 专属凭据而非 NVR 默认凭据。"""
    camera = make_ipc_camera(sourceUrl="rtsp://admin:ipc-pass@172.21.114.8:554/Streaming/Channels/103")
    lookup = make_lookup(
        hosts=("10.10.7.252", "172.21.200.21"),
        mapping=[(128, "172.21.114.8")],
        device_credentials={"172.21.200.21": ("admin", "cvr-pass")},
    )

    async def fake_fetch(self, host):
        return [(128, "172.21.114.8")] if host == "172.21.200.21" else []

    lookup._fetch_channels = fake_fetch.__get__(lookup)
    credentials = asyncio.run(
        resolve_device_credentials(camera, lookup, {"10.10.7.252", "172.21.200.21"})
    )

    assert credentials.host == "172.21.200.21"
    assert credentials.username == "admin"
    assert credentials.password == "cvr-pass"
    assert credentials.channel == 128
    assert credentials.track_id == "12801"


def test_proxy_for_credentials_recreates_on_credential_change():
    """同主机凭据变化时重建代理（如 IPC 凭据换成反查出的 NVR 凭据）。"""
    registry = NvrDeviceRegistry(
        "http://zlm", "http://zlm-public", "secret", "rtmp://zlm/live", 1800, 15
    )
    first = DeviceCredentials("10.10.7.252", "admin", "ipc-pass", 189, "18901")
    second = DeviceCredentials("10.10.7.252", "admin", "nvr-pass", 189, "18901")

    proxy_first = registry.proxy_for_credentials(first)
    assert registry.proxy_for_credentials(first) is proxy_first
    proxy_second = registry.proxy_for_credentials(second)

    assert proxy_second is not proxy_first
    assert proxy_second.password == "nvr-pass"
    assert proxy_second.channel == 189
