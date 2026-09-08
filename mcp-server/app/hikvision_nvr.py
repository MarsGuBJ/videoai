import hashlib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse, urlunparse
from uuid import uuid4
from xml.etree import ElementTree

from .models import Camera, RecordingSegment

NAMESPACE = "http://www.hikvision.com/ver20/XMLSchema"
BEIJING_TZ = timezone(timedelta(hours=8))


class HikvisionError(RuntimeError):
    pass


class HikvisionNvrClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout

    @property
    def _nvr_host(self) -> str:
        parsed = urlparse(self.base_url)
        return parsed.hostname or ""

    async def search_recordings(
        self,
        camera: Camera,
        start_time: datetime,
        end_time: datetime,
        limit: int = 50,
    ) -> list[RecordingSegment]:
        if not self.base_url:
            raise HikvisionError("HIKVISION_NVR_BASE_URL is not configured")
        if not self.username or not self.password:
            raise HikvisionError("Hikvision NVR credentials are not configured")
        track_id = camera.track_id
        if not track_id:
            raise HikvisionError(f"Camera {camera.id} is not bound to a Hikvision track/channel")
        return [
            build_rtsp_direct_recording(
                camera, track_id, start_time, end_time, self._nvr_host, self.username, self.password
            )
        ]

    async def search_by_track(
        self,
        track_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 50,
    ) -> list[RecordingSegment]:
        if not self.base_url:
            raise HikvisionError("HIKVISION_NVR_BASE_URL is not configured")
        if not self.username or not self.password:
            raise HikvisionError("Hikvision NVR credentials are not configured")
        cam = Camera(
            id=f"{self._nvr_host}-track-{track_id}",
            name=f"NVR-{self._nvr_host}-{track_id}",
            sourceUrl="",
            streamApp="live",
            streamName="",
            status="STOPPED",
            playbackUrl="",
            createdAt=start_time,
            updatedAt=start_time,
            nvrId=str(self._nvr_host),
            nvrChannel=track_id,
            nvrTrackId=track_id,
            nvrStreamType="main",
        )
        return [
            build_rtsp_direct_recording(
                cam, track_id, start_time, end_time, self._nvr_host, self.username, self.password
            )
        ]

    async def list_record_tracks(self) -> list[str]:
        return []


def build_search_body(track_id: str, start_time: datetime, end_time: datetime, limit: int) -> str:
    start = format_hik_time(start_time)
    end = format_hik_time(end_time)
    max_results = max(1, min(limit, 200))
    search_id = uuid4()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CMSearchDescription version="1.0" xmlns="{NAMESPACE}">
  <searchID>{search_id}</searchID>
  <trackList>
    <trackID>{track_id}</trackID>
  </trackList>
  <timeSpanList>
    <timeSpan>
      <startTime>{start}</startTime>
      <endTime>{end}</endTime>
    </timeSpan>
  </timeSpanList>
  <maxResults>{max_results}</maxResults>
  <searchResultPosition>0</searchResultPosition>
  <metadataList>
    <metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>
  </metadataList>
</CMSearchDescription>"""


def parse_search_response(
    xml_text: str,
    camera: Camera,
    track_id: str,
    limit: int,
    username: str = "",
    password: str = "",
) -> list[RecordingSegment]:
    root = ElementTree.fromstring(xml_text)  # noqa: S314  # XML 来自内网受信 NVR 的 ISAPI 响应
    matches = root.findall(".//{*}searchMatchItem")
    if not matches and root.tag.endswith("searchMatchItem"):
        matches = [root]

    segments: list[RecordingSegment] = []
    for item in matches[: max(1, limit)]:
        playback_uri = text_at(item, "playbackURI")
        start = parse_hik_time(text_at(item, "startTime"))
        end = parse_hik_time(text_at(item, "endTime"))
        item_track_id = text_at(item, "trackID") or track_id
        if not playback_uri or not start or not end:
            continue
        playback_uri = add_rtsp_credentials(playback_uri, username, password)
        recording_id = stable_recording_id(camera.id, item_track_id, start, end, playback_uri)
        segments.append(
            RecordingSegment(
                recordingId=recording_id,
                cameraId=camera.id,
                cameraName=camera.name,
                trackId=item_track_id,
                startTime=start,
                endTime=end,
                playbackUri=playback_uri,
                metadata={
                    "nvrId": camera.nvrId,
                    "nvrChannel": camera.nvrChannel,
                    "nvrStreamType": camera.nvrStreamType,
                },
            )
        )
    return segments


def add_rtsp_credentials(playback_uri: str, username: str, password: str) -> str:
    parsed = urlparse(playback_uri)
    if parsed.scheme.lower() != "rtsp" or parsed.username or not username:
        return playback_uri
    encoded_user = quote(username, safe="")
    encoded_pass = quote(password, safe="")
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{encoded_user}:{encoded_pass}@{host}{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def text_at(element: ElementTree.Element, tag: str) -> str | None:
    match = element.find(f".//{{*}}{tag}")
    if match is None or match.text is None:
        return None
    value = match.text.strip()
    return value or None


def format_hik_time(value: datetime) -> str:
    """检索时间格式化为北京时间墙钟。海康 ISAPI 把 Z 后缀时间按设备本地时钟解释，
    不能换算成 UTC，否则检索窗口差 8 小时。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(BEIJING_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_hik_time(value: str | None) -> datetime | None:
    """解析 ISAPI 返回的时间。海康返回的是设备本地墙钟时间（即使带 Z 后缀），
    一律按北京时间解释，否则展示/回放时间差 8 小时。"""
    if not value:
        return None
    normalized = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", value.strip())
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.replace(tzinfo=BEIJING_TZ)


def stable_recording_id(camera_id: str, track_id: str, start: datetime, end: datetime, playback_uri: str) -> str:
    digest = hashlib.sha256(
        f"{camera_id}|{track_id}|{start.isoformat()}|{end.isoformat()}|{playback_uri}".encode()
    ).hexdigest()
    return digest[:32]


def _format_rtsp_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    value = value.astimezone(BEIJING_TZ)
    return value.strftime("%Y%m%dT%H%M%SZ")


def build_rtsp_direct_recording(
    camera: Camera,
    track_id: str,
    start_time: datetime,
    end_time: datetime,
    nvr_host: str,
    username: str,
    password: str,
) -> RecordingSegment:
    encoded_user = quote(username, safe="")
    encoded_pass = quote(password, safe="")
    start_str = _format_rtsp_time(start_time)
    end_str = _format_rtsp_time(end_time)
    rtsp_url = (
        f"rtsp://{encoded_user}:{encoded_pass}@{nvr_host}:554"
        f"/Streaming/tracks/{track_id}?starttime={start_str}&endtime={end_str}"
    )
    recording_id = stable_recording_id(camera.id, track_id, start_time, end_time, rtsp_url)
    return RecordingSegment(
        recordingId=recording_id,
        cameraId=camera.id,
        cameraName=camera.name,
        trackId=track_id,
        startTime=start_time,
        endTime=end_time,
        playbackUri=rtsp_url,
        source="hikvision_rtsp_direct",
        metadata={
            "nvrId": camera.nvrId,
            "nvrChannel": camera.nvrChannel,
            "nvrStreamType": camera.nvrStreamType,
            "nvrBaseUrl": f"http://{nvr_host}",
        },
    )


def _build_rtsp_fallback(
    camera: Camera,
    track_id: str,
    start_time: datetime,
    end_time: datetime,
    nvr_host: str,
    username: str,
    password: str,
    max_segments: int = 50,
) -> list[RecordingSegment]:
    encoded_user = quote(username, safe="")
    encoded_pass = quote(password, safe="")

    total_seconds = (end_time - start_time).total_seconds()
    if total_seconds <= 0:
        return []

    chunk_seconds = max(14400, total_seconds / min(max_segments, 50))

    try:
        input_ch = int(track_id) % 100
    except (ValueError, TypeError):
        input_ch = 1
    proxy_ch = 600 + input_ch
    segments: list[RecordingSegment] = []
    chunk_start = start_time
    while chunk_start < end_time and len(segments) < max_segments:
        from datetime import timedelta

        chunk_end = min(chunk_start + timedelta(seconds=chunk_seconds), end_time)
        start_str = _format_rtsp_time(chunk_start)
        end_str = _format_rtsp_time(chunk_end)
        rtsp_url = f"rtsp://{encoded_user}:{encoded_pass}@{nvr_host}:554/Streaming/Channels/{proxy_ch}?starttime={start_str}&endtime={end_str}"
        recording_id = stable_recording_id(camera.id, track_id, chunk_start, chunk_end, rtsp_url)

        segments.append(
            RecordingSegment(
                recordingId=recording_id,
                cameraId=camera.id,
                cameraName=camera.name,
                trackId=track_id,
                startTime=chunk_start,
                endTime=chunk_end,
                playbackUri=rtsp_url,
                source="hikvision_rtsp_fallback",
                metadata={
                    "nvrId": camera.nvrId,
                    "nvrChannel": camera.nvrChannel,
                    "nvrStreamType": camera.nvrStreamType,
                    "nvrBaseUrl": f"http://{nvr_host}",
                },
            )
        )
        chunk_start = chunk_end

    return segments
