"""Recording search, playback and download MCP tools."""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ..context import (
    DEFAULT_RECORDING_RESULT_LIMIT,
    DEFAULT_RECORDING_TIMEZONE,
    DEFAULT_RECORDING_TRACK_ID,
    RECORDING_OVERLAY_TEXT,
    channel_lookup,
    hcnetsdk_downloaders,
    hcnetsdk_playback,
    known_nvr_hosts,
    mcp,
    media_proxy,
    nvr_devices,
    recording_cache,
    recording_mp4_storage,
    settings,
    videoai,
)
from ..hcnetsdk_playback import NET_DVR_PLAYBACK_BY_TIME, HcNetSdkPlaybackProxy
from ..models import Camera, RecordingSegment, StreamResponse
from ..nvr_devices import resolve_device_credentials, search_segments
from ..recording_export import (
    MAX_EXPORT_DURATION_SECONDS,
    MAX_SDK_EXPORT_DURATION_SECONDS,
    RecordingExportError,
    export_recording_mp4,
    export_recording_via_downloader,
    export_recording_via_sdk_download,
)
from ..xml_builder import build_video_file_xml, build_video_list_xml


@mcp.tool()
async def export_recording(trackId: str = "", startTime: str = "", endTime: str = "", cameraId: str = "") -> dict:
    """Export one NVR track's recording for a time range as MP4 to MinIO and return its URL.
    Times are interpreted as Beijing time when no timezone is given. The NVR clock offset is
    measured and compensated automatically. With cameraId the camera's NVR is located first —
    a sourceUrl pointing at a known NVR uses its embedded credentials, a direct-IPC sourceUrl is
    reverse-mapped to its NVR channel via the known NVRs' input channel lists — then downloaded
    via HCNetSDK. Without cameraId, ranges up to 2 hours are downloaded via the whitelist NVR's
    HCNetSDK (non-realtime, fast); if SDK download is unavailable or fails, short ranges (up to
    20 minutes) fall back to RTSP playback capture (~1x wall time)."""
    start = parse_datetime(startTime)
    end = parse_datetime(endTime)
    if end <= start:
        raise ValueError("endTime must be later than startTime")
    duration = (end - start).total_seconds()
    if duration > MAX_SDK_EXPORT_DURATION_SECONDS:
        raise ValueError(f"export duration must not exceed {MAX_SDK_EXPORT_DURATION_SECONDS} seconds")
    camera_id = (cameraId or "").strip()
    if camera_id:
        # 按摄像头定位其 NVR（sourceUrl 直连 IPC 时反查所属 NVR），SDK 按时间下载，非实时抓流
        camera = await videoai.get_camera(camera_id)
        credentials = await resolve_device_credentials(camera, channel_lookup, known_nvr_hosts)
        downloader = nvr_devices.proxy_for_credentials(credentials)
        data = await export_recording_via_downloader(
            downloader, credentials.track_id, credentials.channel, start, end
        )
        return {"data": data}
    track_id = (trackId or "").strip() or DEFAULT_RECORDING_TRACK_ID
    try:
        # SDK 按时间下载，非实时抓流，速度取决于网络带宽
        data = await export_recording_via_sdk_download(track_id, start, end)
    except RecordingExportError as sdk_exc:
        if duration > MAX_EXPORT_DURATION_SECONDS:
            # RTSP 抓流约 1x 且有 20 分钟上限，长时段无法兜底
            raise
        try:
            # 无 SDK 下载器或 SDK 下载失败时，回退 RTSP 回放抓流（约 1x）
            data = await export_recording_mp4(track_id, start, end)
        except RecordingExportError as rtsp_exc:
            raise RecordingExportError(f"sdk download failed: {sdk_exc}; rtsp export failed: {rtsp_exc}") from rtsp_exc
    return {"data": data}


@mcp.tool()
async def search_recordings(
    cameraId: str = "",
    startTime: str = "",
    endTime: str = "",
    limit: int = DEFAULT_RECORDING_RESULT_LIMIT,
    trackId: str = "",
    autoProxy: bool = True,
    streamFormat: str = "flv",
) -> dict:
    """Search an NVR for recordings in a time range and return dynamic playback links.
    With cameraId the camera's NVR is located first — a sourceUrl pointing at a known NVR uses its
    embedded credentials, a direct-IPC sourceUrl is reverse-mapped to its NVR channel via the known
    NVRs' input channel lists — then searched via ISAPI; without cameraId the configured HCNETSDK_*
    device is used. The link (GET /recording-live)
    starts the HCNetSDK playback stream on demand when requested; when the NVR session limit
    is reached, the oldest stream is closed to make room for new ones.
    Returns JSON and XML output."""
    start = parse_datetime(startTime)
    end = parse_datetime(endTime)
    if end <= start:
        raise ValueError("endTime must be later than startTime")

    # 入参回显：随输出一起返回调用方传入的检索条件
    input_echo = {
        "cameraId": cameraId,
        "startTime": startTime,
        "endTime": endTime,
        "limit": limit,
        "trackId": trackId,
        "autoProxy": autoProxy,
        "streamFormat": streamFormat,
    }
    camera_id = (cameraId or "").strip()
    if camera_id:
        result = await search_camera_recordings(camera_id, start, end, limit, autoProxy)
        result["input"] = input_echo
        return result

    failed_tracks: dict[str, str] = {}
    recording = hcnetsdk_playback.build_recording(start, end)
    recording_cache.put_many([recording])
    items = [recording_item(recording)]
    if autoProxy:
        items[0]["url"] = dynamic_recording_url(start, end)
        items[0]["format"] = "flv"
    return {
        "input": input_echo,
        "data": items,
        "xml": build_video_list_xml(items),
        "searchedTrackIds": [recording.trackId],
        "failedTrackIds": failed_tracks,
    }


async def search_camera_recordings(
    camera_id: str,
    start: datetime,
    end: datetime,
    limit: int,
    auto_proxy: bool,
) -> dict:
    """按摄像头检索其所属 NVR 的录像段：ISAPI 检索，回放走该设备的 per-device SDK 代理。

    sourceUrl 直连 IPC 的摄像头经 channel_lookup 反查所属 NVR 与通道。
    """
    camera = await videoai.get_camera(camera_id)
    # 解析 NVR 凭据（反查未命中且未绑定时报 ValueError）
    credentials = await resolve_device_credentials(camera, channel_lookup, known_nvr_hosts)
    recordings = await search_segments(
        camera, start, end, limit, timeout=settings.request_timeout_seconds, credentials=credentials
    )
    recording_cache.put_many(recordings)
    items = [recording_item(recording) for recording in recordings]
    if auto_proxy:
        for recording, item in zip(recordings, items, strict=True):
            item["url"] = camera_recording_url(camera_id, recording.startTime, recording.endTime)
            item["format"] = "flv"
    return {
        "data": items,
        "xml": build_video_list_xml(items),
        "searchedTrackIds": [recording.trackId for recording in recordings] or [credentials.track_id],
        "failedTrackIds": {},
    }


def camera_recording_url(camera_id: str, start: datetime, end: datetime) -> str:
    """按摄像头录像的按需回放链接；流在链接被请求时才建立。"""
    return (
        f"{settings.mcp_public_base_url}/recording-live"
        f"?cameraId={quote(camera_id)}"
        f"&startTime={quote(start.isoformat())}&endTime={quote(end.isoformat())}"
    )


def dynamic_recording_url(start: datetime, end: datetime) -> str:
    """Build the on-demand playback link; the stream is created when the link is requested."""
    return (
        f"{settings.mcp_public_base_url}/recording-live"
        f"?startTime={quote(start.isoformat())}&endTime={quote(end.isoformat())}"
    )


# 现场海康 NVR（10.10.7.252/253）RTSP 回放 Scale 实测支持的倍速档位
PLAYBACK_SPEEDS = (0.25, 0.5, 1, 2, 4, 8, 16, 32)


async def get_recording_stream(recordingId: str, format: str = "flv", speed: float = 1.0) -> dict:
    """Start a short-lived relay for a cached recording and return a playable FLV or HLS URL.

    speed 为回放倍速（仅 SDK 回放源支持；RTSP 转发源不支持倍速）。"""
    if speed not in PLAYBACK_SPEEDS:
        raise ValueError(f"unsupported playback speed: {speed}; supported: {PLAYBACK_SPEEDS}")
    recording = recording_cache.get(recordingId)
    if recording is None:
        raise ValueError("recordingId is unknown or expired; call search_recordings again")
    if recording.source == NET_DVR_PLAYBACK_BY_TIME:
        proxy = await resolve_playback_proxy(recording)
        url = await proxy.start_playback(recording, speed)
        response = StreamResponse(
            url=url,
            format="flv",
            expiresAt=datetime.now(timezone.utc) + timedelta(seconds=settings.playback_ttl_seconds),
            source=recording.source,
            metadata=recording_metadata(recording),
        )
        data = response.model_dump(mode="json")
        data["xml"] = build_video_file_xml(data)
        data["input"] = {"recordingId": recordingId, "format": format, "speed": speed}
        return data
    playback_format = normalize_playback_format(format)
    url = await media_proxy.start_rtsp_relay(
        recording.recordingId,
        recording.playbackUri,
        playback_format,
        overlay_text=RECORDING_OVERLAY_TEXT,
        fallback_file=settings.recording_fallback_file,
    )
    response = StreamResponse(
        url=url,
        format=playback_format,
        expiresAt=datetime.now(timezone.utc) + timedelta(seconds=settings.playback_ttl_seconds),
        source=recording.source,
        metadata=recording_metadata(recording),
    )
    data = response.model_dump(mode="json")
    data["xml"] = build_video_file_xml(data)
    data["input"] = {"recordingId": recordingId, "format": format, "speed": speed}
    return data


async def resolve_playback_proxy(recording: RecordingSegment) -> HcNetSdkPlaybackProxy:
    """Route an SDK playback recording to its device's proxy.

    cameraId 路径检索出的录像（metadata.deviceHost 存在且非单例回放设备）按 recording.cameraId
    再查一次摄像头，经 resolve_device_credentials（含 IPC→NVR 反查）路由到 nvr_devices 中对应
    NVR 的 per-device 代理；其余走单例 hcnetsdk_playback。
    """
    device_host = str(recording.metadata.get("deviceHost") or "")
    if not device_host or device_host == hcnetsdk_playback.host:
        return hcnetsdk_playback
    camera = await videoai.get_camera(recording.cameraId)
    credentials = await resolve_device_credentials(camera, channel_lookup, known_nvr_hosts)
    return nvr_devices.proxy_for_credentials(credentials)


@mcp.tool()
async def download_recording(
    nvr: str = "", startTime: str = "", endTime: str = "", channel: int = 0, trackId: str = "", cameraId: str = ""
) -> dict:
    """Download a recording from the selected NVR through HCNetSDK, save it as MP4 in MinIO, and return the MP4 URL.
    With cameraId the camera's NVR is used instead of the nvr whitelist: a sourceUrl pointing at a known NVR
    uses its embedded credentials, a direct-IPC sourceUrl is reverse-mapped to its NVR channel via the known
    NVRs' input channel lists.
    The channel can be given directly, or derived from trackId (e.g. "201" -> channel 2). The NVR clock
    offset is measured and compensated automatically before downloading."""
    camera_id = (cameraId or "").strip()
    if camera_id:
        camera = await videoai.get_camera(camera_id)
        credentials = await resolve_device_credentials(camera, channel_lookup, known_nvr_hosts)
        downloader = nvr_devices.proxy_for_credentials(credentials)
        start = parse_datetime(startTime)
        end = parse_datetime(endTime)
        if end <= start:
            raise ValueError("endTime must be later than startTime")
        return await download_and_store_recording(downloader, start, end, credentials.channel, camera)

    downloader = resolve_download_nvr(nvr)
    start = parse_datetime(startTime)
    end = parse_datetime(endTime)
    if end <= start:
        raise ValueError("endTime must be later than startTime")

    # trackId（如 201）换算 SDK 通道号（201 -> 2）；显式 channel 优先
    sdk_channel = channel if channel > 0 else 0
    if not sdk_channel and trackId.strip():
        try:
            sdk_channel = int(trackId.strip()) // 100
        except ValueError:
            raise ValueError(f"trackId must be numeric, got: {trackId}") from None
    return await download_and_store_recording(downloader, start, end, sdk_channel or None)


async def download_and_store_recording(
    downloader: HcNetSdkPlaybackProxy,
    start: datetime,
    end: datetime,
    sdk_channel: int | None,
    camera: Camera | None = None,
) -> dict:
    """SDK 按时间下载、remux 并上传 MinIO 的公共流程；展示字段保持用户请求的时间。"""
    failed_tracks: dict[str, str] = {}
    # NVR 时钟偏差补偿：SDK 下载时间按设备本地时钟解释；展示字段保持用户请求的时间，
    # 但不能回写 recording.startTime/endTime——_download_mp4 用它们做 SDK 调用
    skew = await downloader.measure_clock_skew()
    shift = timedelta(seconds=skew)
    recording = downloader.build_download_recording(start + shift, end + shift, sdk_channel)
    if camera is not None:
        recording.cameraId = camera.id
        recording.cameraName = camera.name
    item = recording_item(recording)
    item["startTime"] = start.isoformat()
    item["endTime"] = end.isoformat()
    object_name = f"recordings/{recording.metadata['deviceHost']}/ch{recording.trackId}/{recording.recordingId}.mp4"
    mp4_file = None
    try:
        mp4_file = await downloader.download_mp4(recording)
        url = recording_mp4_storage.upload_mp4(mp4_file, object_name)
        item["url"] = url
        item["format"] = "mp4"
        item["metadata"] = dict(item["metadata"], objectName=object_name)
    except Exception as exc:
        failed_tracks[recording.trackId] = f"HCNetSDK download failed: {exc}"
        raise
    finally:
        if mp4_file is not None:
            mp4_file.unlink(missing_ok=True)
    return {
        "data": [item],
        "xml": build_video_list_xml([item]),
        "searchedTrackIds": [recording.trackId],
        "failedTrackIds": failed_tracks,
    }


def resolve_download_nvr(nvr: str) -> HcNetSdkPlaybackProxy:
    normalized = nvr.strip()
    downloader = hcnetsdk_downloaders.get(normalized)
    if downloader is None:
        allowed = ", ".join(sorted(hcnetsdk_downloaders))
        raise ValueError(f"nvr must be one of: {allowed}")
    return downloader


def parse_datetime(value: str) -> datetime:
    if not value or not value.strip():
        raise ValueError("startTime and endTime are required")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=DEFAULT_RECORDING_TIMEZONE)
    return parsed.astimezone(DEFAULT_RECORDING_TIMEZONE)


def normalize_recording_limit(value: int) -> int:
    return max(1, min(int(value or DEFAULT_RECORDING_RESULT_LIMIT), 200))


def parse_recording_tracks(track_id: str) -> list[str]:
    return unique_recording_tracks(track_id.replace("，", ",").split(","))


def unique_recording_tracks(values) -> list[str]:
    requested = []
    for raw in values:
        track = str(raw or "").strip()
        if track and track not in requested:
            requested.append(track)
    return requested


async def resolve_recording_tracks(track_id: str) -> list[str]:
    requested = parse_recording_tracks(track_id)
    if requested:
        return requested
    return [DEFAULT_RECORDING_TRACK_ID]


async def attach_first_playable_recording_stream(
    items: list[dict],
    recordings: list[RecordingSegment],
    playback_format: str,
    failed_tracks: dict[str, str],
) -> None:
    last_error: Exception | None = None
    for index, recording in enumerate(recordings):
        try:
            items[index]["url"] = await media_proxy.start_rtsp_relay(
                recording.recordingId,
                recording.playbackUri,
                playback_format,
                overlay_text=RECORDING_OVERLAY_TEXT,
                fallback_file=settings.recording_fallback_file,
            )
            items[index]["format"] = playback_format
            return
        except Exception as exc:  # noqa: BLE001  # 逐条尝试，失败原因记入 failed_tracks 后尝试下一条
            last_error = exc
            failed_tracks[recording.trackId] = f"proxy failed: {exc}"
    raise RuntimeError(f"no recording stream could be proxied: {last_error}") from last_error


def per_track_recording_limit(total_limit: int, track_count: int) -> int:
    if track_count <= 0:
        return total_limit
    return max(1, (total_limit + track_count - 1) // track_count)


def normalize_playback_format(value: str) -> str:
    normalized = (value or "flv").strip().lower()
    if normalized not in {"flv", "hls"}:
        raise ValueError("format must be flv or hls")
    return normalized


def recording_item(recording: RecordingSegment) -> dict:
    return dict(
        recording.model_dump(mode="json", exclude={"playbackUri", "metadata"}),
        metadata=safe_metadata(recording.metadata),
    )


def recording_metadata(recording: RecordingSegment) -> dict:
    return dict(
        safe_metadata(recording.metadata),
        cameraId=recording.cameraId,
        cameraName=recording.cameraName,
        recordingId=recording.recordingId,
        trackId=recording.trackId,
        startTime=recording.startTime,
        endTime=recording.endTime,
    )


def safe_metadata(metadata: dict) -> dict:
    sensitive_keys = {"nvrUsername", "nvrPassword", "username", "password"}
    return {key: value for key, value in metadata.items() if key not in sensitive_keys}
