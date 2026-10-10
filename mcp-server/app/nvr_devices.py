"""按摄像头定位其绑定的 NVR 设备：凭据解析、多设备 SDK 回放代理注册表与 ISAPI 录像检索。

现场摄像头均绑定 NVR/设备：``sourceUrl`` 形如 ``rtsp://user:pass@<nvrIP>:554/Streaming/Channels/101``，
内嵌的 user/pass 同时可用于该设备的 ISAPI（Digest）与 HCNetSDK 登录（默认端口 8000）。
sourceUrl 直连 IPC 的摄像头（录像存在某台 NVR 上）通过 ``NvrChannelLookup`` 反查所属 NVR 与通道。
注意：任何日志/异常消息都不得包含设备密码。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import threading
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

import httpx

from .hcnetsdk_playback import NET_DVR_PLAYBACK_BY_TIME, HcNetSdkPlaybackProxy
from .hikvision_nvr import build_search_body, parse_hik_time, text_at
from .models import Camera, RecordingSegment

logger = logging.getLogger(__name__)

DEFAULT_SDK_PORT = 8000
SDK_PORT_ENV = "HCNETSDK_DEVICE_PORT"


class NvrDeviceError(RuntimeError):
    """Raised when a camera-bound NVR device cannot be reached or searched."""


@dataclass(frozen=True)
class DeviceCredentials:
    """从摄像头 sourceUrl 与 NVR 绑定字段解析出的设备登录凭据。"""

    host: str
    username: str
    password: str
    channel: int
    track_id: str
    sdk_port: int = DEFAULT_SDK_PORT
    # 流ID 模式存储设备（如现场 DS-A CVR）的录像流标识；非空时 SDK 回放/下载按流ID定位，
    # 忽略 channel（这类设备 ISAPI 关闭、通道回放返回"流ID不存在"）
    stream_id: str = ""


def parse_device_credentials(
    camera: Camera, sdk_port: int | None = None, fallback_track_id: str = ""
) -> DeviceCredentials:
    """Parse the NVR device credentials bound to a camera.

    通道号优先取 ``nvrChannel``，否则由 ``nvrTrackId`` 换算（如 "201" -> 通道 2）。
    两者都缺失时用 ``fallback_track_id``（仅 sourceUrl 指向录像设备本体时由调用方
    从 URL 路径提取，见 ``resolve_device_credentials``）。

    Raises:
        ValueError: 摄像头未绑定 NVR，或 sourceUrl 无法解析出主机/用户名/密码时。
    """
    port = sdk_port or int(os.getenv(SDK_PORT_ENV, "") or DEFAULT_SDK_PORT)
    track_id = (camera.nvrTrackId or camera.nvrChannel or "").strip() or fallback_track_id
    if not track_id:
        raise ValueError(f"camera {camera.id} is not bound to an NVR: nvrTrackId/nvrChannel is missing")
    source_url = (camera.sourceUrl or "").strip()
    if not source_url:
        raise ValueError(f"camera {camera.id} has no sourceUrl to derive NVR device credentials from")
    parsed = urlparse(source_url)
    host = parsed.hostname or ""
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    if not host or not username or not password:
        raise ValueError(f"camera {camera.id} sourceUrl does not embed device host/username/password")
    return DeviceCredentials(
        host=host,
        username=username,
        password=password,
        channel=resolve_device_channel(camera, track_id),
        track_id=track_id,
        sdk_port=port,
    )


TRACK_ID_PATH_PATTERN = re.compile(r"/Streaming/(?:Channels|tracks)/(\d+)", re.IGNORECASE)


def track_id_from_source_url(source_url: str) -> str:
    """从录像设备的 sourceUrl 路径提取 trackId（如 /Streaming/Channels/12801 → "12801"）。

    仅对 sourceUrl 指向 NVR/CVR 本体的摄像头可靠；取不到时返回 ""。
    """
    match = TRACK_ID_PATH_PATTERN.search(urlparse(source_url).path or "")
    return match.group(1) if match else ""


def resolve_device_channel(camera: Camera, track_id: str) -> int:
    """Return the SDK channel number: explicit nvrChannel first, else trackId // 100."""
    raw_channel = (camera.nvrChannel or "").strip()
    try:
        if raw_channel:
            return int(raw_channel)
        return int(track_id) // 100
    except ValueError:
        raise ValueError(
            f"camera {camera.id} nvrChannel/nvrTrackId must be numeric, got: {raw_channel or track_id}"
        ) from None


def parse_input_proxy_channels(xml_text: str) -> list[tuple[int, str]]:
    """解析 NVR 的 InputProxyChannel 列表为 (通道号, 源 IPC 地址) 列表。"""
    root = ElementTree.fromstring(xml_text)  # noqa: S314  # XML 来自内网受信设备的 ISAPI 响应
    channels: list[tuple[int, str]] = []
    for item in root.findall(".//{*}InputProxyChannel"):
        channel_id = text_at(item, "id")
        ip_address = text_at(item, "ipAddress")
        if channel_id and ip_address:
            channels.append((int(channel_id), ip_address))
    return channels


class NvrChannelLookup:
    """IPC → 录像设备（NVR/CVR）通道反查：拉取各已知设备的 ISAPI 输入代理通道列表，按源 IPC 地址建映射。

    结果整体缓存 ``ttl_seconds``；单台设备不可达或认证失败只记日志，不阻塞其余设备。
    默认凭据用 NVR 设备的（与下载白名单一致），``device_credentials`` 可为凭据不同的设备
    （如 CVR）按主机覆盖；反查命中哪个设备就用哪个设备的凭据登录。
    """

    def __init__(
        self,
        hosts: Sequence[str],
        username: str,
        password: str,
        timeout: float = 15,
        ttl_seconds: int = 600,
        device_credentials: Mapping[str, tuple[str, str]] | None = None,
    ) -> None:
        self.hosts = tuple(hosts)
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ttl_seconds = ttl_seconds
        self._device_credentials = dict(device_credentials or {})
        self._cache: dict[str, tuple[str, int]] = {}
        self._expires_at = 0.0

    def credentials_for(self, host: str) -> tuple[str, str]:
        """返回指定录像设备的登录凭据：优先设备专属凭据，否则默认凭据。"""
        return self._device_credentials.get(host, (self.username, self.password))

    async def lookup(self, ipc_host: str) -> tuple[str, int] | None:
        """返回 IPC 所属的 (设备主机, 通道号)；不在任何已知设备上时返回 None。"""
        now = time.monotonic()
        if now < self._expires_at:
            return self._cache.get(ipc_host)
        self._cache = await self._fetch_all()
        self._expires_at = now + self.ttl_seconds
        return self._cache.get(ipc_host)

    async def _fetch_all(self) -> dict[str, tuple[str, int]]:
        # 并发拉取各设备通道列表，避免单台不可达设备拖慢整体反查
        results = await asyncio.gather(*(self._fetch_channels_safe(host) for host in self.hosts))
        mapping: dict[str, tuple[str, int]] = {}
        for host, channels in zip(self.hosts, results, strict=True):
            for channel, ip_address in channels:
                mapping.setdefault(ip_address, (host, channel))
        return mapping

    async def _fetch_channels_safe(self, host: str) -> list[tuple[int, str]]:
        try:
            return await self._fetch_channels(host)
        except Exception as exc:  # noqa: BLE001  # 单台设备失败不阻塞整体反查；消息不含密码
            logger.warning("NVR channel lookup failed on %s: %s", host, type(exc).__name__)
            return []

    async def _fetch_channels(self, host: str) -> list[tuple[int, str]]:
        username, password = self.credentials_for(host)
        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(username, password),
            timeout=self.timeout,
        ) as client:
            response = await client.get(f"http://{host}/ISAPI/ContentMgmt/InputProxy/channels")
            response.raise_for_status()
        return parse_input_proxy_channels(response.text)


# 绑定存储设备通道反查的 per-host 缓存 TTL（与 NvrChannelLookup 一致）
BINDING_CHANNEL_TTL_SECONDS = 600
# host -> (过期时间, 通道列表)；凭据随绑定传入，TTL 内凭据变更按缓存容忍
_binding_channel_cache: dict[str, tuple[float, list[tuple[int, str]]]] = {}


async def lookup_bound_storage_channel(
    host: str,
    username: str,
    password: str,
    ipc_host: str,
    timeout: float = 15,
) -> int | None:
    """用绑定凭据反查存储设备上 IPC 对应的通道号；请求失败或未命中返回 None（消息不含密码）。"""
    now = time.monotonic()
    cached = _binding_channel_cache.get(host)
    if cached is None or now >= cached[0]:
        try:
            async with httpx.AsyncClient(
                auth=httpx.DigestAuth(username, password),
                timeout=timeout,
            ) as client:
                response = await client.get(f"http://{host}/ISAPI/ContentMgmt/InputProxy/channels")
                response.raise_for_status()
            channels = parse_input_proxy_channels(response.text)
        except Exception as exc:  # noqa: BLE001  # 反查失败回退平台通道字段；消息不含密码
            logger.warning("bound storage channel lookup failed on %s: %s", host, type(exc).__name__)
            return None
        cached = (now + BINDING_CHANNEL_TTL_SECONDS, channels)
        _binding_channel_cache[host] = cached
    for channel, ip_address in cached[1]:
        if ip_address == ipc_host:
            return channel
    return None


# 绑定前录像校验的查询窗口（天）：只查最近一段时间，避免全时段检索过慢；
# 窗口远大于设备时钟偏差，无需做时钟补偿
BINDING_VERIFY_RECENT_DAYS = 30


async def verify_storage_recording(
    camera: Camera,
    host: str,
    username: str,
    password: str,
    recent_days: int = BINDING_VERIFY_RECENT_DAYS,
    timeout: float = 15,
) -> str | None:
    """校验存储设备上是否查得到该摄像头的录像；通过返回 None，否则返回原因（不含密码）。

    依次检查：sourceUrl 可定位 IPC → 设备输入代理通道列表中存在该 IPC →
    最近 ``recent_days`` 天该通道有录像。任一不满足都不应把摄像头关联到这台存储设备
    （通道都没有说明设备选错；有通道没录像说明录像不在这台设备上）。
    """
    ipc_host = urlparse((camera.sourceUrl or "").strip()).hostname or ""
    if not ipc_host:
        return "摄像头未配置 sourceUrl，无法在存储设备上定位通道"
    channel = await lookup_bound_storage_channel(host, username, password, ipc_host, timeout=timeout)
    if channel is None:
        return f"存储设备 {host} 的输入通道列表中没有该摄像头（{ipc_host}），或设备不可达/凭据无效"
    credentials = DeviceCredentials(
        host=host,
        username=username,
        password=password,
        channel=channel,
        track_id=str(channel * 100 + 1),
    )
    # 查询窗口必须 tz-aware：search_segments 会把窗口与海康返回的 tz-aware 时段比较裁剪
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=recent_days)
    try:
        segments = await search_segments(
            camera, start_time, end_time, limit=1, timeout=timeout, credentials=credentials
        )
    except NvrDeviceError as exc:
        return str(exc)
    if not segments:
        return f"存储设备 {host} 上最近 {recent_days} 天查询不到该摄像头的录像"
    return None


async def resolve_device_credentials(
    camera: Camera,
    channel_lookup: NvrChannelLookup | None,
    known_nvr_hosts: Collection[str],
    binding: Mapping[str, str] | None = None,
) -> DeviceCredentials:
    """解析摄像头录像检索/回放/下载应使用的 NVR 设备凭据。

    - ``binding``（平台关联的录像存储设备）非空时优先：主机/凭据直接取自绑定；绑定带
      流ID（``streamId``）时按流ID直接回放（ISAPI 不可用的流ID模式设备）；否则通道用
      绑定凭据反查该设备 ISAPI 输入代理通道列表（按 sourceUrl 的 IP 匹配），
      反查未命中/失败时回退平台 nvrChannel/nvrTrackId（主机/凭据仍用绑定的）；
    - ``sourceUrl`` 指向已知 NVR/CVR：沿用内嵌凭据与 nvrTrackId/nvrChannel 换算的通道；
      平台未填 trackId 时从 sourceUrl 路径兜底（如 /Streaming/Channels/12801 → track 12801）；
    - ``sourceUrl`` 直连 IPC：反查已知 NVR/CVR 的输入通道映射，命中时用该设备的凭据与
      实际通道号（直连 IPC 的平台 nvrTrackId 可能是批量导入的脏数据，不作准）；
    - 反查未命中：回退原解析逻辑（未绑定 NVR 时报 ``ValueError``，消息注明反查未命中）。
    """
    if binding:
        return await _credentials_from_binding(camera, binding)
    host = urlparse((camera.sourceUrl or "").strip()).hostname or ""
    if not host or host in known_nvr_hosts or channel_lookup is None:
        # sourceUrl 指向录像设备本体时，trackId 可从 URL 通道路径兜底
        fallback = track_id_from_source_url(camera.sourceUrl or "") if host in known_nvr_hosts else ""
        return parse_device_credentials(camera, fallback_track_id=fallback)
    hit = await channel_lookup.lookup(host)
    if hit is None:
        try:
            return parse_device_credentials(camera)
        except ValueError as exc:
            raise ValueError(
                f"{exc}; IPC {host} reverse lookup missed:"
                " not found in any known NVR/CVR input channel list"
            ) from None
    nvr_host, channel = hit
    username, password = channel_lookup.credentials_for(nvr_host)
    return DeviceCredentials(
        host=nvr_host,
        username=username,
        password=password,
        channel=channel,
        track_id=str(channel * 100 + 1),
    )


async def _credentials_from_binding(camera: Camera, binding: Mapping[str, str]) -> DeviceCredentials:
    """按平台关联的录像存储设备解析凭据：主机/凭据取自绑定，通道自动反查。

    绑定含 ``streamId`` 时直接按流ID回放：这类设备（现场 DS-A CVR）ISAPI 关闭，
    反查必然失败且失败无缓存会白等超时，通道回放也不可用（按通道起播报"流ID不存在"）。
    否则通道用绑定凭据拉取该设备 ISAPI InputProxy 通道列表，按摄像头 sourceUrl 的 IP 匹配；
    反查未命中/失败时回退平台 nvrChannel/nvrTrackId（主机/凭据仍用绑定的）；
    完全没有通道信息时报 ``ValueError``。
    """
    host = (binding.get("host") or "").strip()
    username = (binding.get("username") or "").strip()
    password = binding.get("password") or ""
    if not host or not username or not password:
        raise ValueError(f"camera {camera.id} storage binding is incomplete: host/username/password required")
    stream_id = (binding.get("streamId") or "").strip()
    if stream_id:
        return DeviceCredentials(
            host=host,
            username=username,
            password=password,
            channel=0,
            track_id=stream_id,
            stream_id=stream_id,
        )
    ipc_host = urlparse((camera.sourceUrl or "").strip()).hostname or ""
    channel = await lookup_bound_storage_channel(host, username, password, ipc_host) if ipc_host else None
    if channel is not None:
        return DeviceCredentials(
            host=host,
            username=username,
            password=password,
            channel=channel,
            track_id=str(channel * 100 + 1),
        )
    # 反查未命中/失败：回退平台侧通道字段，主机与凭据仍用绑定的
    track_id = (camera.nvrTrackId or camera.nvrChannel or "").strip()
    if not track_id:
        raise ValueError(f"camera {camera.id} 未在关联存储设备 {host} 上反查到通道，且平台未配置 nvrChannel/nvrTrackId")
    return DeviceCredentials(
        host=host,
        username=username,
        password=password,
        channel=resolve_device_channel(camera, track_id),
        track_id=track_id,
    )


async def effective_storage_host(
    camera: Camera,
    channel_lookup: NvrChannelLookup | None,
    known_nvr_hosts: Collection[str],
    binding: Mapping[str, str] | None = None,
) -> str | None:
    """返回摄像头实际生效的录像存储设备主机（供平台"录像存储配置"展示），解析不到返回 None。

    优先级与 ``resolve_device_credentials`` 一致：显式绑定 > sourceUrl 指向已知 NVR/CVR >
    直连 IPC 反查已知设备的输入通道。仅做主机定位，不涉及凭据。
    """
    bound_host = ((binding or {}).get("host") or "").strip()
    if bound_host:
        return bound_host
    host = urlparse((camera.sourceUrl or "").strip()).hostname or ""
    if not host:
        return None
    if host in known_nvr_hosts:
        return host
    if channel_lookup is None:
        return None
    hit = await channel_lookup.lookup(host)
    return hit[0] if hit else None


class NvrDeviceRegistry:
    """按设备主机懒创建并缓存 HCNetSDK 回放代理（线程安全）。"""

    def __init__(
        self,
        zlm_http_url: str,
        zlm_public_http_url: str,
        zlm_secret: str,
        zlm_rtmp_push_base: str,
        ttl_seconds: int,
        timeout: float = 15,
        sdk_port: int | None = None,
        max_live_sessions: int = 0,
    ) -> None:
        self.zlm_http_url = zlm_http_url
        self.zlm_public_http_url = zlm_public_http_url
        self.zlm_secret = zlm_secret
        self.zlm_rtmp_push_base = zlm_rtmp_push_base
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self.sdk_port = sdk_port
        self.max_live_sessions = max_live_sessions
        self._proxies: dict[str, HcNetSdkPlaybackProxy] = {}
        self._lock = threading.Lock()

    def proxy_for(self, camera: Camera) -> HcNetSdkPlaybackProxy:
        """Return the cached playback proxy for the camera's NVR device, creating it on first use."""
        return self.proxy_for_credentials(parse_device_credentials(camera, self.sdk_port))

    def proxy_for_credentials(self, credentials: DeviceCredentials) -> HcNetSdkPlaybackProxy:
        """Return the cached playback proxy for explicit device credentials.

        同主机凭据变化（如 IPC 凭据 → 反查出的 NVR 凭据）时重建代理。
        """
        with self._lock:
            proxy = self._proxies.get(credentials.host)
            if proxy is None or (proxy.username, proxy.password) != (credentials.username, credentials.password):
                proxy = HcNetSdkPlaybackProxy(
                    credentials.host,
                    credentials.sdk_port,
                    credentials.username,
                    credentials.password,
                    credentials.channel,
                    self.zlm_http_url,
                    self.zlm_public_http_url,
                    self.zlm_secret,
                    self.zlm_rtmp_push_base,
                    self.ttl_seconds,
                    self.timeout,
                    max_live_sessions=self.max_live_sessions,
                )
                self._proxies[credentials.host] = proxy
            return proxy


async def search_segments(
    camera: Camera,
    start_time: datetime,
    end_time: datetime,
    limit: int = 50,
    timeout: float = 15,
    credentials: DeviceCredentials | None = None,
) -> list[RecordingSegment]:
    """Search the camera's NVR for recordings via ISAPI and map matches to SDK playback segments.

    设备无录像时返回空列表；设备不可达或认证失败时抛 ``NvrDeviceError``（消息不含密码）。
    ``credentials`` 可由调用方经 ``resolve_device_credentials`` 预解析（含 IPC→NVR 反查）。
    """
    credentials = credentials or parse_device_credentials(camera)
    body = build_search_body(credentials.track_id, start_time, end_time, limit)
    try:
        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(credentials.username, credentials.password),
            timeout=timeout,
        ) as client:
            response = await client.post(
                f"http://{credentials.host}/ISAPI/ContentMgmt/search",
                content=body,
                headers={"Content-Type": "application/xml"},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise NvrDeviceError(
            f"NVR recording search failed on {credentials.host}: HTTP {exc.response.status_code}"
            " (device rejected the request or credentials are invalid)"
        ) from exc
    except httpx.HTTPError as exc:
        raise NvrDeviceError(f"NVR {credentials.host} is unreachable: {type(exc).__name__}") from exc
    segments = parse_segment_matches(response.text, camera, credentials, limit)
    # 海康 ISAPI 返回的是与窗口相交的整个连续录像块（不裁剪到查询窗口），
    # 裁剪到用户查询窗口，避免搜一小时却列出数小时的录像段
    return [
        clipped
        for segment in segments
        if (clipped := clip_segment_to_window(segment, start_time, end_time)) is not None
    ]


def clip_segment_to_window(
    segment: RecordingSegment,
    start_time: datetime,
    end_time: datetime,
) -> RecordingSegment | None:
    """Clip one segment to the query window; ``None`` when there is no overlap.

    recordingId 随裁剪后的时间重算：同一录像块在不同查询窗口下裁剪结果不同，
    不重算会共享缓存键导致回放取到别的窗口。
    """
    clipped_start = max(segment.startTime, start_time)
    clipped_end = min(segment.endTime, end_time)
    if clipped_end <= clipped_start:
        return None
    if clipped_start == segment.startTime and clipped_end == segment.endTime:
        return segment
    segment.startTime = clipped_start
    segment.endTime = clipped_end
    segment.recordingId = segment_recording_id(
        str(segment.metadata.get("deviceHost") or ""),
        segment.trackId,
        clipped_start,
        clipped_end,
    )
    return segment


def parse_segment_matches(
    xml_text: str,
    camera: Camera,
    credentials: DeviceCredentials,
    limit: int,
) -> list[RecordingSegment]:
    """Map ISAPI searchMatchItem entries to SDK playback recording segments."""
    root = ElementTree.fromstring(xml_text)  # noqa: S314  # XML 来自内网受信设备的 ISAPI 响应
    matches = root.findall(".//{*}searchMatchItem")
    if not matches and root.tag.endswith("searchMatchItem"):
        matches = [root]
    segments: list[RecordingSegment] = []
    for item in matches[: max(1, limit)]:
        segment = segment_from_match(item, camera, credentials)
        if segment is not None:
            segments.append(segment)
    return segments


def segment_from_match(
    item: ElementTree.Element,
    camera: Camera,
    credentials: DeviceCredentials,
) -> RecordingSegment | None:
    """Build one SDK playback segment from a searchMatchItem; ``None`` when times are missing."""
    start = parse_hik_time(text_at(item, "startTime"))
    end = parse_hik_time(text_at(item, "endTime"))
    if start is None or end is None:
        return None
    track_id = text_at(item, "trackID") or credentials.track_id
    recording_id = segment_recording_id(credentials.host, track_id, start, end)
    return RecordingSegment(
        recordingId=recording_id,
        cameraId=camera.id,
        cameraName=camera.name,
        trackId=track_id,
        startTime=start,
        endTime=end,
        playbackUri=f"hcnetsdk://{credentials.host}:{credentials.sdk_port}/channels/{credentials.channel}",
        source=NET_DVR_PLAYBACK_BY_TIME,
        metadata={
            "deviceHost": credentials.host,
            "devicePort": credentials.sdk_port,
            "channel": credentials.channel,
            # 密码绝不写入 metadata/日志；username 在对外输出时由 safe_metadata 剔除
            "username": credentials.username,
            "protocol": "HCNetSDK",
            "sdkApi": "NET_DVR_PlayBackByTime_V40",
        },
    )


def segment_recording_id(host: str, track_id: str, start_time: datetime, end_time: datetime) -> str:
    """Return a deterministic 32-char recording id for a host/track/time-range tuple."""
    digest = hashlib.sha256(f"{host}|{track_id}|{start_time.isoformat()}|{end_time.isoformat()}".encode()).hexdigest()
    return digest[:32]
