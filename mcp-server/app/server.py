"""VideoAI MCP server assembly: shared context, tool registrations, HTTP routes and MCP resources.

Tool implementations live under ``app.tools`` (grouped by domain) and the HTTP
wrapper routes in ``app.routes``; this module wires everything together and
re-exports the public surface for tests and embedding.
"""

from . import tools as tools
from .context import (
    DINO_DEFAULT_CAMERA_NAMES,
    DINO_EVENT_COUNT,
    DINO_EVENT_LEVEL,
    DINO_EVENT_SOURCE,
    DINO_EVENT_STATUS,
    DINO_EVENT_TYPE,
    hcnetsdk_downloaders,
    hcnetsdk_playback,
    hikvision,
    mcp,
    media_proxy,
    person_api,
    recording_cache,
    recording_mp4_storage,
    settings,
    videoai,
)
from .hcnetsdk_playback import NET_DVR_PLAYBACK_BY_TIME
from .routes import register_http_tool_routes
from .tools import (
    detect_persons,
    detect_persons_with_id,
    dino_events,
    download_recording,
    gait_feature_compare,
    get_live_stream,
    get_person_bbox,
    get_person_search_result,
    get_recording_stream,
    list_cameras,
    query_face_matches,
    search_person_by_bbox,
    search_recordings,
    upload_face_image,
)
from .tools.cameras import detect_format
from .tools.dino import build_mock_dino_events, normalize_dino_event_limit
from .tools.recordings import (
    attach_first_playable_recording_stream,
    normalize_playback_format,
    normalize_recording_limit,
    parse_datetime,
    parse_recording_tracks,
    per_track_recording_limit,
    recording_item,
    recording_metadata,
    resolve_download_nvr,
    resolve_recording_tracks,
    safe_metadata,
    unique_recording_tracks,
)

__all__ = [
    "DINO_DEFAULT_CAMERA_NAMES",
    "DINO_EVENT_COUNT",
    "DINO_EVENT_LEVEL",
    "DINO_EVENT_SOURCE",
    "DINO_EVENT_STATUS",
    "DINO_EVENT_TYPE",
    "NET_DVR_PLAYBACK_BY_TIME",
    "attach_first_playable_recording_stream",
    "build_mock_dino_events",
    "detect_format",
    "detect_persons",
    "detect_persons_with_id",
    "dino_events",
    "download_recording",
    "gait_feature_compare",
    "get_live_stream",
    "get_person_bbox",
    "get_person_search_result",
    "get_recording_stream",
    "hcnetsdk_downloaders",
    "hcnetsdk_playback",
    "hikvision",
    "list_cameras",
    "mcp",
    "media_proxy",
    "normalize_dino_event_limit",
    "normalize_playback_format",
    "normalize_recording_limit",
    "parse_datetime",
    "parse_recording_tracks",
    "per_track_recording_limit",
    "person_api",
    "query_face_matches",
    "recording_cache",
    "recording_item",
    "recording_metadata",
    "recording_mp4_storage",
    "resolve_download_nvr",
    "resolve_recording_tracks",
    "safe_metadata",
    "search_person_by_bbox",
    "search_recordings",
    "settings",
    "tools",
    "unique_recording_tracks",
    "upload_face_image",
    "videoai",
]


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


register_http_tool_routes()

if __name__ == "__main__":
    mcp.run(transport=settings.mcp_transport)  # type: ignore[arg-type]
