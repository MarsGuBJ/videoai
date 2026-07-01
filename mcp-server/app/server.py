from datetime import datetime, timezone
from typing import Literal

from mcp.server.fastmcp import FastMCP

from .hikvision_isapi import HikvisionIsapiClient
from .media_proxy import MediaProxy
from .models import StreamResponse
from .recording_cache import RecordingCache
from .settings import load_settings
from .videoai_client import VideoAiClient
from .xml_builder import (
    build_camera_flow_xml,
    build_camera_list_xml,
    build_video_file_xml,
    build_video_list_xml,
)


settings = load_settings()

mcp = FastMCP(
    "videoai-monitoring",
    instructions="Query VideoAI cameras and create live or Hikvision NVR recording playback URLs.",
    host=settings.mcp_host,
    port=settings.mcp_port,
    streamable_http_path="/mcp",
    sse_path="/sse",
)

videoai = VideoAiClient(settings.videoai_base_url, settings.request_timeout_seconds)
hikvision = HikvisionIsapiClient(
    settings.hikvision_base_url,
    settings.hikvision_username,
    settings.hikvision_password,
    settings.request_timeout_seconds,
)
media_proxy = MediaProxy(
    settings.zlm_http_url,
    settings.zlm_public_http_url,
    settings.zlm_secret,
    settings.zlm_rtmp_push_base,
    settings.playback_ttl_seconds,
    settings.request_timeout_seconds,
)
recording_cache = RecordingCache(settings.playback_ttl_seconds)


@mcp.tool()
async def list_cameras() -> dict:
    """List live cameras configured in VideoAI, excluding NVR-only recording channels. Returns JSON and XML output."""
    cameras = await videoai.list_cameras()
    live_cameras = [c for c in cameras if not _is_nvr_only_channel(c)]
    items = [
        {
            "cameraId": camera.id,
            "name": camera.name,
            "status": camera.status,
            "livePlaybackUrl": _public_url(camera.playbackUrl),
            "sourceUrl": camera.sourceUrl,
            "nvrBinding": {
                "bound": camera.nvr_bound,
                "nvrId": camera.nvrId,
                "nvrChannel": camera.nvrChannel,
                "nvrTrackId": camera.nvrTrackId,
                "nvrStreamType": camera.nvrStreamType,
            },
        }
        for camera in live_cameras
    ]
    return {
        "data": items,
        "xml": build_camera_list_xml(items),
    }


@mcp.tool()
async def get_live_stream(cameraId: str, autoStart: bool = True) -> dict:
    """Return a playable live stream URL for one camera. Returns JSON and XML output."""
    camera = await videoai.get_camera(cameraId)
    if autoStart and camera.status != "RUNNING":
        camera = await videoai.start_camera(cameraId)
    url = _public_url(camera.playbackUrl)
    response = StreamResponse(
        url=url,
        format=detect_format(url),
        expiresAt=None,
        source="live",
        metadata={
            "cameraId": camera.id,
            "cameraName": camera.name,
            "status": camera.status,
            "streamApp": camera.streamApp,
            "streamName": camera.streamName,
        },
    )
    data = response.model_dump(mode="json")
    data["xml"] = build_camera_flow_xml(data)
    return data


@mcp.tool()
async def search_recordings(cameraId: str = "", startTime: str = "", endTime: str = "", limit: int = 50, trackId: str = "") -> dict:
    """Search Hikvision NVR recordings by camera, track, or across all tracks.
    If cameraId is provided, searches that camera's bound track.
    If trackId is provided (without cameraId), searches that track directly.
    If neither is provided, searches across all 58 tracks (101-158).
    Returns JSON and XML output."""
    start = parse_datetime(startTime) if startTime else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    end = parse_datetime(endTime) if endTime else datetime.now(timezone.utc)
    if end <= start:
        raise ValueError("endTime must be after startTime")
    bounded_limit = max(1, min(limit, 200))

    all_recordings: list = []
    if cameraId:
        camera = await videoai.get_camera(cameraId)
        recordings = await hikvision.search_recordings(camera, start, end, bounded_limit)
        all_recordings = recordings
    elif trackId:
        recordings = await hikvision.search_by_track(trackId, start, end, bounded_limit)
        all_recordings = recordings
    else:
        sub_limit = max(1, bounded_limit // 10)
        for t in range(101, 159):
            try:
                recordings = await hikvision.search_by_track(str(t), start, end, sub_limit)
                all_recordings.extend(recordings)
            except Exception:
                continue

    recording_cache.put_many(all_recordings)
    items = [recording.model_dump(mode="json", exclude={"playbackUri"}) for recording in all_recordings]
    return {
        "data": items,
        "xml": build_video_list_xml(items),
    }


@mcp.tool()
async def get_recording_stream(
    recordingId: str = "",
    trackId: str = "",
    nvrBaseUrl: str = "",
    nvrUsername: str = "",
    nvrPassword: str = "",
    format: Literal["hls"] = "hls",
) -> dict:
    """Return a playable video stream URL for a recording. Two calling modes:
    1. By recordingId: looks up the cached recording from search_recordings.
    2. By direct params: trackId, nvrBaseUrl, nvrUsername, nvrPassword.
    Uses ZLMediaKit ffmpeg relay to convert NVR RTSP to HLS.
    Returns JSON and XML output."""
    recording = recording_cache.get(recordingId) if recordingId else None
    if recording is None:
        if not trackId or not nvrBaseUrl:
            raise ValueError("Provide recordingId from search_recordings, or trackId + nvrBaseUrl")
        from urllib.parse import urlparse
        host = urlparse(nvrBaseUrl).hostname or ""
        username = nvrUsername or "admin"
        password = nvrPassword or ""
        from .models import Camera, RecordingSegment
        cam = Camera(id=trackId, name=f"NVR-{trackId}", sourceUrl="", streamApp="live", streamName="",
                      status="STOPPED", playbackUrl="", createdAt=datetime.now(timezone.utc),
                      updatedAt=datetime.now(timezone.utc), nvrId=host, nvrChannel=trackId,
                      nvrTrackId=trackId, nvrStreamType="main")
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        end = datetime.now(timezone.utc)
        recordings = await hikvision.search_by_track(trackId, start, end, 1)
        if recordings:
            recording = recordings[0]
        else:
            raise ValueError(f"No recording found for track {trackId}")
        recording_cache.put_many([recording])
    response = await media_proxy.open_recording_stream(recording, format)
    data = response.model_dump(mode="json")
    data["xml"] = build_video_file_xml(data)
    return data


@mcp.tool()
async def upload_face_image(imageBase64: str, cameraId: str, modelName: str, name: str = "人脸库照片") -> dict:
    """Upload a face image (base64 encoded) to the face library. The face library holds exactly one image;
    uploading a new image replaces the previous one. Returns a faceId for use in query_face_matches.
    cameraId and modelName are required parameters for future use (currently not activated)."""
    result = await videoai.upload_face(imageBase64, cameraId, modelName, name)
    return result


@mcp.tool()
async def query_face_matches(faceId: str = "", limit: int = 10) -> dict:
    """Query face match events identified by the face library.
    If faceId is provided, returns matching events for that specific face.
    If faceId is empty, returns the latest match events across all faces (max 10).
    Results are sorted by video time descending."""
    matches = await videoai.query_face_matches(faceId if faceId else None, limit)
    return {"data": matches, "count": len(matches)}


@mcp.resource("videoai://cameras/{cameraId}")
async def camera_resource(cameraId: str) -> dict:
    """Return one camera resource."""
    camera = await videoai.get_camera(cameraId)
    return camera.model_dump(mode="json")


@mcp.resource("videoai://recordings/{recordingId}")
async def recording_resource(recordingId: str) -> dict:
    """Return one cached recording resource without sensitive playback URI."""
    recording = recording_cache.get(recordingId)
    if recording is None:
        raise ValueError("recordingId is unknown or expired; call search_recordings again")
    return recording.model_dump(mode="json", exclude={"playbackUri"})


def _is_nvr_only_channel(camera) -> bool:
    """Return True if this camera is an NVR recording channel only (no live source)."""
    name = (camera.name or "").lower()
    if name.startswith("nvr") or "nvr-only" in name:
        return True
    return False


def _public_url(url: str) -> str:
    """Resolve a playback URL to the publicly accessible base URL.
    For relative /live/ paths, use ZLM_PUBLIC_HTTP_URL (or fallback to backend)."""
    public_base = settings.zlm_public_http_url or settings.videoai_base_url
    return videoai.absolute_url(url, public_base=public_base)


def parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def detect_format(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".m3u8"):
        return "hls"
    if lower.endswith(".flv"):
        return "flv"
    if lower.endswith(".mjpeg"):
        return "mjpeg"
    if lower.startswith("rtsp://"):
        return "rtsp"
    return "url"


if __name__ == "__main__":
    mcp.run(transport=settings.mcp_transport)  # type: ignore[arg-type]
