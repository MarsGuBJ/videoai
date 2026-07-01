from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from .models import RecordingSegment, StreamResponse


class MediaProxy:
    def __init__(
        self,
        zlm_http_url: str,
        zlm_public_http_url: str,
        zlm_secret: str,
        zlm_rtmp_push_base: str,
        ttl_seconds: int,
        timeout: float = 15,
    ) -> None:
        self.zlm_http_url = zlm_http_url.rstrip("/")
        self.zlm_public_http_url = zlm_public_http_url.rstrip("/")
        self.zlm_secret = zlm_secret
        self.zlm_rtmp_push_base = zlm_rtmp_push_base.rstrip("/")
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout

    async def open_recording_stream(self, recording: RecordingSegment, fmt: str = "hls") -> StreamResponse:
        if recording.source == "hikvision_rtsp_fallback":
            stream_name = f"recording-{recording.recordingId}"
            dst_url = f"{self.zlm_rtmp_push_base}/{stream_name}"
            await self._add_ffmpeg_source(recording.playbackUri, dst_url)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
            return StreamResponse(
                url=f"{self.zlm_public_http_url}/live/{quote(stream_name, safe='')}.m3u8",
                format="hls",
                expiresAt=expires_at,
                source="hikvision_rtsp_fallback",
                metadata=recording.metadata,
            )

        if fmt != "hls":
            raise ValueError("Only hls recording playback is supported")
        stream_name = f"recording-{recording.recordingId}"
        dst_url = f"{self.zlm_rtmp_push_base}/{stream_name}"
        await self._add_ffmpeg_source(recording.playbackUri, dst_url)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        return StreamResponse(
            url=f"{self.zlm_public_http_url}/live/{quote(stream_name, safe='')}.m3u8",
            format="hls",
            expiresAt=expires_at,
            source=recording.source,
            metadata=recording.metadata,
        )

    async def _add_ffmpeg_source(self, source_url: str, dst_url: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.zlm_http_url}/index/api/addFFmpegSource",
                params={
                    "secret": self.zlm_secret,
                    "src_url": source_url,
                    "dst_url": dst_url,
                    "timeout_ms": 15000,
                },
            )
            response.raise_for_status()
            payload = response.json()
            code = str(payload.get("code", "0"))
            if code != "0":
                raise RuntimeError(f"ZLMediaKit rejected recording source: {payload}")
