from collections.abc import Awaitable, Callable
import asyncio
from datetime import datetime, timedelta, timezone
from inspect import Parameter, signature
from typing import Any
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .hikvision_nvr import HikvisionNvrClient
from .hcnetsdk_playback import HcNetSdkPlaybackProxy, NET_DVR_PLAYBACK_BY_TIME
from .media_proxy import MediaProxy
from .minio_storage import RecordingMp4Storage
from .models import RecordingSegment, StreamResponse
from .person_api_client import PersonApiClient
from .recording_cache import RecordingCache
from .settings import load_settings
from .videoai_client import VideoAiClient
from .xml_builder import (
    build_camera_flow_xml,
    build_camera_list_xml,
    build_dino_event_list_xml,
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
person_api = PersonApiClient(settings.person_api_base_url, settings.request_timeout_seconds)
hikvision = HikvisionNvrClient(
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
hcnetsdk_playback = HcNetSdkPlaybackProxy(
    settings.hcnetsdk_host,
    settings.hcnetsdk_port,
    settings.hcnetsdk_username,
    settings.hcnetsdk_password,
    settings.hcnetsdk_channel,
    settings.zlm_http_url,
    settings.zlm_public_http_url,
    settings.zlm_secret,
    settings.zlm_rtmp_push_base,
    settings.playback_ttl_seconds,
    settings.request_timeout_seconds,
)
hcnetsdk_downloaders = {
    host: HcNetSdkPlaybackProxy(
        host,
        settings.hcnetsdk_download_port,
        settings.hcnetsdk_download_username,
        settings.hcnetsdk_download_password,
        settings.hcnetsdk_download_channel,
        settings.zlm_http_url,
        settings.zlm_public_http_url,
        settings.zlm_secret,
        settings.zlm_rtmp_push_base,
        settings.playback_ttl_seconds,
        settings.request_timeout_seconds,
    )
    for host in settings.hcnetsdk_download_nvr_hosts
}
recording_mp4_storage = RecordingMp4Storage(
    settings.minio_endpoint,
    settings.minio_port,
    settings.minio_use_ssl,
    settings.minio_access_key,
    settings.minio_secret_key,
    settings.minio_bucket,
)
recording_cache = RecordingCache(settings.playback_ttl_seconds)
DEFAULT_RECORDING_RESULT_LIMIT = 50
SEARCH_RECORDINGS_RESULT_LIMIT = 1
DEFAULT_RECORDING_TRACK_ID = "601"
DEFAULT_RECORDING_TIMEZONE = timezone(timedelta(hours=8))
RECORDING_OVERLAY_TEXT = ""
DINO_EVENT_SOURCE = "视觉平台"
DINO_EVENT_TYPE = "DINO Object Detection"
DINO_EVENT_STATUS = "有效"
DINO_EVENT_LEVEL = 1
DINO_EVENT_COUNT = 10
DINO_DEFAULT_CAMERA_NAMES = (
    "摄像头101",
    "摄像头102",
    "摄像头103",
    "摄像头104",
    "摄像头105",
)


@mcp.tool()
async def list_cameras() -> dict:
    """List live cameras configured in VideoAI, excluding NVR-only recording channels. Returns JSON and XML output."""
    cameras = await videoai.list_cameras()
    live_cameras = [c for c in cameras if not _is_nvr_only_channel(c)]
    items = []
    for camera in live_cameras:
        live_url = _public_url(camera.playbackUrl)
        items.append(
            {
                "cameraId": camera.id,
                "name": camera.name,
                "status": camera.status,
                "url": live_url,
                "livePlaybackUrl": live_url,
                "sourceUrl": camera.sourceUrl,
                "nvrBinding": {
                    "bound": camera.nvr_bound,
                    "nvrId": camera.nvrId,
                    "nvrChannel": camera.nvrChannel,
                    "nvrTrackId": camera.nvrTrackId,
                    "nvrStreamType": camera.nvrStreamType,
                },
            }
        )
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
async def search_recordings(
    cameraId: str = "",
    startTime: str = "",
    endTime: str = "",
    limit: int = DEFAULT_RECORDING_RESULT_LIMIT,
    trackId: str = "",
    autoProxy: bool = True,
    streamFormat: str = "flv",
) -> dict:
    """Create one HCNetSDK private-protocol playback stream from 192.168.11.198 for a time range.
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
    object_name = (
        f"recordings/{recording.metadata['deviceHost']}/ch{recording.trackId}/{recording.recordingId}.mp4"
    )
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


@mcp.tool()
async def upload_face_image(imageUrl: str, cameraId: str, modelName: str, name: str = "人脸库照片") -> dict:
    """Upload a face image URL, create an enabled face deployment task for cameraId, and return both records.
    The task is visible on the deployment task page and starts in running status."""
    face_result = await videoai.upload_face(imageUrl, cameraId, modelName, name)
    face_id = str(face_result.get("faceId") or face_result.get("id") or "").strip()
    if not face_id:
        raise ValueError("face upload response did not include faceId")

    face_profile = await videoai.get_face(face_id)
    task_payload = {
        "name": name or face_profile.get("name") or "人脸识别布控",
        "pipeline": modelName or "人脸识别流程",
        "area": "默认区域",
        "areaCount": 1,
        "enabled": True,
        "desc": "MCP upload_face_image 自动创建",
        "faceProfileId": face_id,
        "faceProfileName": face_profile.get("name") or name,
        "faceProfilePhotoUrl": face_profile.get("photoUrl"),
        "cameraIds": [cameraId],
    }
    deployment_task = await videoai.create_deployment_task(task_payload)
    return {
        "faceId": face_id,
        "face": face_profile,
        "deploymentTaskId": deployment_task.get("id"),
        "deploymentTask": deployment_task,
    }


@mcp.tool()
async def query_face_matches(faceId: str = "", limit: int = 10) -> dict:
    """Query face match events identified by the face library.
    If faceId is provided, returns matching events for that specific face.
    If faceId is empty, returns the latest match events across all faces (max 10).
    Results are sorted by video time descending."""
    matches = await videoai.query_face_matches(faceId if faceId else None, limit)
    return {"data": matches, "count": len(matches)}


@mcp.tool()
async def detect_persons(imageUrl: str) -> dict:
    """Detect persons in an image URL and return person bounding boxes."""
    return await person_api.detect_persons(imageUrl)


@mcp.tool()
async def search_person_by_bbox(
    imageUrl: str,
    bbox: list[dict[str, Any]] | None = None,
    searchMethod: str = "reid",
    startTime: str = "",
    endTime: str = "",
    similarityThreshold: float = 0.6,
    topK: int = 10,
) -> dict:
    """Submit an async person image search task, optionally restricted to a bbox."""
    return await person_api.search_person_by_bbox(
        imageUrl,
        bbox=bbox,
        search_method=searchMethod,
        start_time=startTime,
        end_time=endTime,
        similarity_threshold=similarityThreshold,
        top_k=topK,
    )


@mcp.tool()
async def get_person_search_result(taskId: str) -> dict:
    """Poll a person image search task result by taskId."""
    return await person_api.get_person_search_result(taskId)


@mcp.tool()
async def detect_persons_with_id(imageUrl: str) -> dict:
    """Detect persons in an image URL and return cached person IDs with bounding boxes."""
    return await person_api.detect_persons_with_id(imageUrl)


@mcp.tool()
async def get_person_bbox(personId: str) -> dict:
    """Return cached bbox information for a personId from detect_persons_with_id."""
    return await person_api.get_person_bbox(personId)


@mcp.tool()
async def gait_feature_compare(persons: list[dict[str, Any]]) -> dict:
    """Compare gait features for a list of person records; the first person is the reference."""
    return await person_api.gait_feature_compare(persons)


@mcp.tool()
async def dino_events(limit: int = DINO_EVENT_COUNT) -> dict:
    """Return mock DINO Object Detection events for visual event search."""
    camera_names = await load_dino_event_camera_names()
    descriptions = await load_dino_event_descriptions()
    items = build_mock_dino_events(
        camera_names=camera_names,
        descriptions=descriptions,
        count=normalize_dino_event_limit(limit),
    )
    return {
        "data": items,
        "count": len(items),
        "xml": build_dino_event_list_xml(items),
    }


def register_http_tool_routes() -> None:
    tool_handlers = {
        "list_cameras": list_cameras,
        "get_live_stream": get_live_stream,
        "search_recordings": search_recordings,
        "get_recording_stream": get_recording_stream,
        "download_recording": download_recording,
        "upload_face_image": upload_face_image,
        "query_face_matches": query_face_matches,
        "detect_persons": detect_persons,
        "search_person_by_bbox": search_person_by_bbox,
        "get_person_search_result": get_person_search_result,
        "detect_persons_with_id": detect_persons_with_id,
        "get_person_bbox": get_person_bbox,
        "gait_feature_compare": gait_feature_compare,
        "dino_events": dino_events,
    }
    for tool_name, handler in tool_handlers.items():
        register_http_tool_route(tool_name, handler)


def register_http_tool_route(tool_name: str, handler: Callable[..., Awaitable[dict]]) -> None:
    @mcp.custom_route(f"/{tool_name}-http", methods=["POST"], name=f"{tool_name}_http")
    async def http_tool_endpoint(request: Request, _handler=handler) -> JSONResponse:
        try:
            arguments = await parse_http_arguments(request, _handler)
            result = await _handler(**arguments)
            return JSONResponse(json_safe(result))
        except ValueError as exc:
            return JSONResponse(error_payload("ValueError", str(exc)), status_code=400)
        except Exception as exc:
            return JSONResponse(error_payload(type(exc).__name__, "internal server error"), status_code=500)


async def parse_http_arguments(request: Request, handler: Callable[..., Awaitable[dict]]) -> dict[str, Any]:
    payload = await read_json_object(request)
    params = {
        name: param
        for name, param in signature(handler).parameters.items()
        if param.kind in {Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}
    }
    unknown = sorted(set(payload) - set(params))
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(unknown)}")
    missing = sorted(
        name
        for name, param in params.items()
        if param.default is Parameter.empty and name not in payload
    )
    if missing:
        raise ValueError(f"missing required parameter(s): {', '.join(missing)}")
    return {
        name: convert_http_argument(name, value, params[name].annotation)
        for name, value in payload.items()
    }


async def read_json_object(request: Request) -> dict[str, Any]:
    body = await request.body()
    if not body:
        return {}
    try:
        payload = await request.json()
    except Exception as exc:
        raise ValueError("request body must be a JSON object") from exc
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def convert_http_argument(name: str, value: Any, annotation: Any) -> Any:
    if annotation is bool:
        return convert_http_bool(name, value)
    if annotation is int:
        return convert_http_int(name, value)
    if annotation is float:
        return convert_http_float(name, value)
    if annotation is str:
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)
    return value


def convert_http_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    raise ValueError(f"{name} must be a boolean")


def convert_http_int(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def convert_http_float(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return json_safe(value.model_dump(mode="json"))
    return value


def error_payload(error_type: str, message: str) -> dict:
    return {"error": {"type": error_type, "message": message}}


register_http_tool_routes()


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
    return recording_item(recording)


async def load_dino_event_camera_names() -> list[str]:
    try:
        cameras = await videoai.list_cameras()
    except Exception:
        return list(DINO_DEFAULT_CAMERA_NAMES)
    names = [camera.name for camera in cameras if camera.name]
    return names or list(DINO_DEFAULT_CAMERA_NAMES)


async def load_dino_event_descriptions() -> list[str]:
    try:
        tasks = await videoai.list_deployment_tasks()
    except Exception:
        return []
    descriptions: list[str] = []
    for task in tasks:
        searchable = " ".join(str(task.get(key) or "") for key in ("name", "pipeline")).lower()
        if "dino" not in searchable:
            continue
        description = str(task.get("desc") or "").strip()
        if description:
            descriptions.append(description)
    return descriptions


def build_mock_dino_events(
    camera_names: list[str] | None = None,
    descriptions: list[str] | None = None,
    count: int = DINO_EVENT_COUNT,
    base_time: datetime | None = None,
) -> list[dict]:
    names = camera_names or list(DINO_DEFAULT_CAMERA_NAMES)
    notes = descriptions or []
    now = base_time or datetime.now(DEFAULT_RECORDING_TIMEZONE)
    if now.tzinfo is None:
        now = now.replace(tzinfo=DEFAULT_RECORDING_TIMEZONE)
    events = []
    for index in range(normalize_dino_event_limit(count)):
        occurred_at = now - timedelta(minutes=index * 5)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=DEFAULT_RECORDING_TIMEZONE)
        description = notes[index % len(notes)] if notes else "无"
        events.append(
            {
                "eventId": f"dino-mock-{index + 1:03d}",
                "eventSource": DINO_EVENT_SOURCE,
                "eventType": DINO_EVENT_TYPE,
                "eventStatus": DINO_EVENT_STATUS,
                "eventLevel": DINO_EVENT_LEVEL,
                "eventLocation": names[index % len(names)],
                "occurredAt": occurred_at.isoformat(),
                "reportedAt": occurred_at.isoformat(),
                "eventImage": build_mock_dino_event_image(index + 1, names[index % len(names)]),
                "eventDescription": description,
            }
        )
    return events


def normalize_dino_event_limit(value: int) -> int:
    return max(1, min(int(value or DINO_EVENT_COUNT), DINO_EVENT_COUNT))


def build_mock_dino_event_image(index: int, camera_name: str) -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<rect width="640" height="360" fill="#111827"/>'
        '<rect x="28" y="28" width="584" height="304" fill="#1f2937" stroke="#60a5fa" stroke-width="4"/>'
        '<text x="48" y="78" fill="#e5e7eb" font-family="Arial, sans-serif" font-size="28">DINO Object Detection</text>'
        f'<text x="48" y="132" fill="#93c5fd" font-family="Arial, sans-serif" font-size="24">{camera_name}</text>'
        f'<text x="48" y="188" fill="#f9fafb" font-family="Arial, sans-serif" font-size="48">视频截图 {index:02d}</text>'
        '<rect x="410" y="168" width="128" height="86" fill="none" stroke="#22c55e" stroke-width="5"/>'
        '<text x="410" y="150" fill="#22c55e" font-family="Arial, sans-serif" font-size="22">object</text>'
        "</svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")


def _is_nvr_only_channel(camera) -> bool:
    """Return True if this camera is an NVR recording channel only (no live source)."""
    return not (camera.sourceUrl or "").strip()


def _public_url(url: str) -> str:
    """Resolve a playback URL to the publicly accessible base URL.
    For relative /live/ paths, use ZLM_PUBLIC_HTTP_URL (or fallback to backend)."""
    public_base = settings.zlm_public_http_url or settings.videoai_base_url
    return videoai.absolute_url(url, public_base=public_base)


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
        except Exception as exc:
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
    return dict(recording.model_dump(mode="json", exclude={"playbackUri", "metadata"}), metadata=safe_metadata(recording.metadata))


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
