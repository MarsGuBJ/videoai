from __future__ import annotations

import asyncio

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
        self._semaphore = asyncio.Semaphore(10)
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    def _stream_name(self, uid: str) -> str:
        return f"rec-{uid[:12]}"

    def _hls_url(self, stream_name: str) -> str:
        return f"{self.zlm_public_http_url}/live/{stream_name}/hls.m3u8"

    async def start_rtsp_relay(self, uid: str, rtsp_url: str) -> str:
        stream_name = self._stream_name(uid)
        hls_url = self._hls_url(stream_name)

        if stream_name in self._processes:
            proc = self._processes[stream_name]
            if proc.returncode is not None:
                del self._processes[stream_name]
            else:
                return hls_url

        async with self._semaphore:
            if stream_name in self._processes:
                return hls_url
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-rtsp_transport", "tcp",
                    "-i", rtsp_url,
                    "-c", "copy",
                    "-f", "flv",
                    "-loglevel", "error",
                    f"{self.zlm_rtmp_push_base}/{stream_name}",
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                self._processes[stream_name] = proc
            except Exception:
                pass

        return hls_url
