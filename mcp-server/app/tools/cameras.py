"""Camera listing and live-stream MCP tools."""

from ..context import mcp, settings, videoai
from ..models import StreamResponse
from ..xml_builder import build_camera_flow_xml, build_camera_list_xml

DEFAULT_CAMERA_PAGE_SIZE = 20
MAX_CAMERA_PAGE_SIZE = 200


@mcp.tool()
async def list_cameras(name: str = "", page: int = 1, pageSize: int = DEFAULT_CAMERA_PAGE_SIZE) -> dict:
    """List live cameras configured in VideoAI, excluding NVR-only recording channels.
    name filters cameras by a case-insensitive substring of the camera name; page/pageSize
    paginate the result (page starts at 1). Each item returns id, status, url and name,
    where status reflects device online status (RUNNING = online, STOPPED = offline).
    Returns JSON and XML output."""
    cameras = await videoai.list_cameras()
    live_cameras = [c for c in cameras if not _is_nvr_only_channel(c)]
    keyword = (name or "").strip().lower()
    if keyword:
        live_cameras = [c for c in live_cameras if keyword in (c.name or "").lower()]
    page = max(1, int(page or 1))
    page_size = max(1, min(int(pageSize or DEFAULT_CAMERA_PAGE_SIZE), MAX_CAMERA_PAGE_SIZE))
    total = len(live_cameras)
    offset = (page - 1) * page_size
    items = [
        {
            "id": camera.id,
            "status": _online_status(camera),
            "url": _public_url(camera.playbackUrl),
            "name": camera.name,
        }
        for camera in live_cameras[offset : offset + page_size]
    ]
    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
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
    data["input"] = {"cameraId": cameraId, "autoStart": autoStart}
    return data


def _is_nvr_only_channel(camera) -> bool:
    """Return True if this camera is an NVR recording channel only (no live source)."""
    return not (camera.sourceUrl or "").strip()


def _online_status(camera) -> str:
    """Map device online status to the public status enum: online = RUNNING, otherwise STOPPED."""
    return "RUNNING" if (camera.onlineStatus or "").upper() == "ONLINE" else "STOPPED"


def _public_url(url: str) -> str:
    """Resolve a playback URL to the publicly accessible base URL.
    For relative /live/ paths, use ZLM_PUBLIC_HTTP_URL (or fallback to backend)."""
    public_base = settings.zlm_public_http_url or settings.videoai_base_url
    return videoai.absolute_url(url, public_base=public_base)


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
