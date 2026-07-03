from datetime import datetime, timezone
from urllib.parse import quote, urlparse
from xml.etree import ElementTree

import httpx

from .models import Camera, RecordingSegment


NAMESPACE = "http://www.hikvision.com/ver20/XMLSchema"


class HikvisionError(RuntimeError):
    pass


class HikvisionIsapiClient:
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
        return await self._do_search(track_id, camera, start_time, end_time, limit)

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
        import uuid
        cam = Camera(
            id=str(uuid.uuid4())[:32],
            name=f"NVR-{track_id}",
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
        return await self._do_search(track_id, cam, start_time, end_time, limit)

    async def _do_search(
        self,
        track_id: str,
        camera: Camera,
        start_time: datetime,
        end_time: datetime,
        limit: int = 50,
    ) -> list[RecordingSegment]:
        body = build_search_body(track_id, start_time, end_time, limit)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, auth=httpx.DigestAuth(self.username, self.password)) as client:
                response = await client.post(
                    f"{self.base_url}/ISAPI/ContentMgmt/search",
                    content=body.encode("utf-8"),
                    headers={"Content-Type": "application/xml"},
                )
                if response.status_code == 401:
                    async with httpx.AsyncClient(timeout=self.timeout, auth=(self.username, self.password)) as basic_client:
                        response = await basic_client.post(
                            f"{self.base_url}/ISAPI/ContentMgmt/search",
                            content=body.encode("utf-8"),
                            headers={"Content-Type": "application/xml"},
                        )
                if response.status_code == 400 and "badXmlContent" in response.text:
                    return _build_rtsp_fallback(camera, track_id, start_time, end_time, self._nvr_host, self.username, self.password, limit)
                response.raise_for_status()
            return parse_search_response(response.text, camera, track_id, limit)
        except (httpx.HTTPStatusError, httpx.HTTPError, httpx.RequestError, HikvisionError, Exception):
            return _build_rtsp_fallback(camera, track_id, start_time, end_time, self._nvr_host, self.username, self.password, limit)


def build_search_body(track_id: str, start_time: datetime, end_time: datetime, limit: int) -> str:
    start = format_hik_time(start_time)
    end = format_hik_time(end_time)
    max_results = max(1, min(limit, 200))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CMSearchDescription>
  <searchID>{track_id}-{int(start_time.timestamp())}-{int(end_time.timestamp())}</searchID>
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


def parse_search_response(xml_text: str, camera: Camera, track_id: str, limit: int) -> list[RecordingSegment]:
    root = ElementTree.fromstring(xml_text)
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


def text_at(element: ElementTree.Element, tag: str) -> str | None:
    match = element.find(f".//{{*}}{tag}")
    if match is None or match.text is None:
        return None
    value = match.text.strip()
    return value or None


def format_hik_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_hik_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def stable_recording_id(camera_id: str, track_id: str, start: datetime, end: datetime, playback_uri: str) -> str:
    import hashlib

    digest = hashlib.sha256(f"{camera_id}|{track_id}|{start.isoformat()}|{end.isoformat()}|{playback_uri}".encode()).hexdigest()
    return digest[:32]


def _format_rtsp_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y%m%dT%H%M%SZ")


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
    snapshot_url = f"http://{nvr_host}/ISAPI/ContentMgmt/StreamingProxy/channels/{proxy_ch}/picture"

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
                    "snapshotUrl": snapshot_url,
                    "nvrUsername": username,
                    "nvrPassword": password,
                    "nvrBaseUrl": f"http://{nvr_host}",
                },
            )
        )
        chunk_start = chunk_end

    return segments
