"""Recording search, playback and download MCP tools."""

from datetime import datetime, timedelta, timezone

from ..context import (
    DEFAULT_RECORDING_RESULT_LIMIT,
    DEFAULT_RECORDING_TIMEZONE,
    DEFAULT_RECORDING_TRACK_ID,
    RECORDING_OVERLAY_TEXT,
    hcnetsdk_downloaders,
    hcnetsdk_playback,
    mcp,
    media_proxy,
    recording_cache,
    recording_mp4_storage,
    settings,
)
from ..hcnetsdk_playback import NET_DVR_PLAYBACK_BY_TIME, HcNetSdkPlaybackProxy
from ..models import RecordingSegment, StreamResponse
from ..xml_builder import build_video_file_xml, build_video_list_xml


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
    """Create one HCNetSDK private-protocol playback stream from the configured NVR for a time range.
    The returned stream is an FLV URL backed by NET_DVR_PlayBackByTime_V40 callback data.
    Returns JSON and XML output."""
    start = parse_datetime(startTime)
    end = parse_datetime(endTime)
    if end <= start:
        raise ValueError("endTime must be later than startTime")

    failed_tracks: dict[str, str] = {}
    recording = hcnetsdk_playback.build_recording(start, end)
    recording_cache.put_many([recording])
    items = [recording_item(recording)]
    if autoProxy:
        try:
            items[0]["url"] = await hcnetsdk_playback.start_playback(recording)
            items[0]["format"] = "flv"
        except Exception as exc:
            failed_tracks[recording.trackId] = f"HCNetSDK playback failed: {exc}"
            raise
    return {
        "data": items,
        "xml": build_video_list_xml(items),
        "searchedTrackIds": [recording.trackId],
        "failedTrackIds": failed_tracks,
    }


async def get_recording_stream(recordingId: str, format: str = "flv") -> dict:
    """Start a short-lived relay for a cached recording and return a playable FLV or HLS URL."""
    recording = recording_cache.get(recordingId)
    if recording is None:
        raise ValueError("recordingId is unknown or expired; call search_recordings again")
    if recording.source == NET_DVR_PLAYBACK_BY_TIME:
        url = await hcnetsdk_playback.start_playback(recording)
        response = StreamResponse(
            url=url,
            format="flv",
            expiresAt=datetime.now(timezone.utc) + timedelta(seconds=settings.playback_ttl_seconds),
            source=recording.source,
            metadata=recording_metadata(recording),
        )
        data = response.model_dump(mode="json")
        data["xml"] = build_video_file_xml(data)
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
    return data


@mcp.tool()
async def download_recording(nvr: str, startTime: str = "", endTime: str = "") -> dict:
    """Download a recording from the selected NVR through HCNetSDK, save it as MP4 in MinIO, and return the MP4 URL."""
    downloader = resolve_download_nvr(nvr)
    start = parse_datetime(startTime)
    end = parse_datetime(endTime)
    if end <= start:
        raise ValueError("endTime must be later than startTime")

    failed_tracks: dict[str, str] = {}
    recording = downloader.build_download_recording(start, end)
    item = recording_item(recording)
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
