from __future__ import annotations

import asyncio
import contextlib
import time
from pathlib import Path

import httpx


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
        self._semaphore = asyncio.Semaphore(1)
        self._processes: dict[str, tuple[float, asyncio.subprocess.Process]] = {}

    def _stream_name(self, uid: str) -> str:
        return f"rec-{uid[:12]}"

    def _hls_url(self, stream_name: str) -> str:
        return f"{self.zlm_public_http_url}/live/{stream_name}/hls.m3u8"

    def _flv_url(self, stream_name: str) -> str:
        return f"{self.zlm_public_http_url}/live/{stream_name}.live.flv"

    def _playback_url(self, stream_name: str, output_format: str) -> str:
        if output_format == "hls":
            return self._hls_url(stream_name)
        return self._flv_url(stream_name)

    async def start_rtsp_relay(
        self,
        uid: str,
        rtsp_url: str,
        output_format: str = "flv",
        wait_ready: bool = True,
        overlay_text: str = "",
        fallback_file: str = "",
    ) -> str:
        stream_name = self._stream_name(uid)
        playback_url = self._playback_url(stream_name, output_format)
        self._cleanup_expired()

        async with self._semaphore:
            await self._stop_all_recording_relays()

            if not wait_ready:
                await self._stop_external_recording_processes()
                proc = await self._start_ffmpeg(stream_name, rtsp_url, overlay_text)
                self._remember_process(stream_name, proc)
                return playback_url

            last_error: Exception | None = None
            max_attempts = 6
            for attempt in range(max_attempts):
                await self._stop_external_recording_processes()
                proc = await self._start_ffmpeg(stream_name, rtsp_url, overlay_text)
                self._remember_process(stream_name, proc)
                try:
                    await self._wait_until_ready(stream_name, proc)
                    return playback_url
                except asyncio.CancelledError:
                    await self._terminate_and_wait(stream_name, proc)
                    raise
                except (RuntimeError, TimeoutError) as exc:
                    last_error = exc
                    await self._terminate_and_wait(stream_name, proc)
                    if fallback_file and await _is_file(fallback_file) and "453" in str(exc):
                        break
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(min(2 * (attempt + 1), 10))

            if fallback_file and await _is_file(fallback_file):
                proc = await self._start_file_ffmpeg(stream_name, fallback_file, overlay_text)
                self._remember_process(stream_name, proc)
                try:
                    await self._wait_until_ready(stream_name, proc)
                    return playback_url
                except asyncio.CancelledError:
                    await self._terminate_and_wait(stream_name, proc)
                    raise
                except (RuntimeError, TimeoutError) as exc:
                    last_error = exc
                    await self._terminate_and_wait(stream_name, proc)

            raise RuntimeError(f"recording stream relay was not ready after retry: {last_error}") from last_error

        return playback_url

    async def _start_ffmpeg(
        self, stream_name: str, rtsp_url: str, overlay_text: str = ""
    ) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            *self._rtsp_ffmpeg_args(stream_name, rtsp_url, overlay_text),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    def _rtsp_ffmpeg_args(self, stream_name: str, rtsp_url: str, overlay_text: str = "") -> list[str]:
        args = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-re",
            "-rtsp_transport",
            "tcp",
            "-i",
            rtsp_url,
        ]
        if overlay_text:
            args.extend(
                [
                    "-vf",
                    self._overlay_filter(overlay_text),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-tune",
                    "zerolatency",
                ]
            )
        else:
            args.extend(["-an", "-c:v", "copy"])
        args.extend(
            [
                "-f",
                "flv",
                f"{self.zlm_rtmp_push_base}/{stream_name}",
            ]
        )
        return args

    async def _start_file_ffmpeg(
        self, stream_name: str, source_file: str, overlay_text: str = ""
    ) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            *self._file_ffmpeg_args(stream_name, source_file, overlay_text),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    def _file_ffmpeg_args(self, stream_name: str, source_file: str, overlay_text: str = "") -> list[str]:
        args = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-re",
            "-stream_loop",
            "-1",
            "-i",
            source_file,
        ]
        if overlay_text:
            args.extend(
                [
                    "-vf",
                    self._overlay_filter(overlay_text),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-tune",
                    "zerolatency",
                ]
            )
        else:
            args.extend(["-an", "-c:v", "copy"])
        args.extend(
            [
                "-f",
                "flv",
                f"{self.zlm_rtmp_push_base}/{stream_name}",
            ]
        )
        return args

    def _overlay_filter(self, overlay_text: str) -> str:
        safe_text = overlay_text.replace("\\", "\\\\").replace(":", "\\:").replace(",", "\\,").replace("'", "\\'")
        return (
            "drawbox=x=0:y=0:w=1250:h=130:color=black@1.0:t=fill,"
            "drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
            f"text={safe_text}:x=60:y=35:fontsize=56:fontcolor=white"
        )

    def _remember_process(self, stream_name: str, proc: asyncio.subprocess.Process) -> None:
        expires_at = time.monotonic() + max(self.ttl_seconds, 1)
        self._processes[stream_name] = (expires_at, proc)
        asyncio.create_task(self._stop_after_ttl(stream_name, proc, expires_at))

    async def _wait_until_ready(self, stream_name: str, proc: asyncio.subprocess.Process) -> None:
        deadline = time.monotonic() + min(max(self.timeout, 5), 30)
        while time.monotonic() < deadline:
            if proc.returncode is not None:
                self._processes.pop(stream_name, None)
                error = await self._read_process_error(proc)
                detail = f": {error}" if error else ""
                raise RuntimeError(f"ffmpeg exited before recording stream was ready: {stream_name}{detail}")
            if await self._stream_exists(stream_name):
                return
            await asyncio.sleep(0.5)
        raise TimeoutError(f"recording stream was not ready before timeout: {stream_name}")

    async def _stream_exists(self, stream_name: str) -> bool:
        params = f"secret={self.zlm_secret}"
        url = f"{self.zlm_http_url}/index/api/getMediaList?{params}"
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5)) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return False
        if payload.get("code") != 0:
            return False
        return any(item.get("stream") == stream_name for item in payload.get("data") or [])

    async def _recording_stream_names(self) -> set[str]:
        params = f"secret={self.zlm_secret}"
        url = f"{self.zlm_http_url}/index/api/getMediaList?{params}"
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5)) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return set()
        if payload.get("code") != 0:
            return set()
        return {
            item.get("stream") for item in payload.get("data") or [] if is_recording_stream_name(item.get("stream"))
        }

    async def _wait_until_recording_streams_closed(self) -> None:
        deadline = time.monotonic() + min(max(self.timeout, 5), 15)
        while time.monotonic() < deadline:
            if not await self._recording_stream_names():
                return
            await asyncio.sleep(0.5)

    def _cleanup_expired(self) -> None:
        now = time.monotonic()
        for stream_name, (expires_at, proc) in list(self._processes.items()):
            if proc.returncode is not None:
                del self._processes[stream_name]
            elif expires_at <= now:
                self._terminate(stream_name, proc)

    async def _stop_after_ttl(self, stream_name: str, proc: asyncio.subprocess.Process, expires_at: float) -> None:
        await asyncio.sleep(max(self.ttl_seconds, 1))
        current = self._processes.get(stream_name)
        if current is None or current[1] is not proc or current[0] != expires_at:
            return
        self._terminate(stream_name, proc)

    def _terminate(self, stream_name: str, proc: asyncio.subprocess.Process) -> None:
        self._processes.pop(stream_name, None)
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()
            with contextlib.suppress(RuntimeError):
                asyncio.create_task(proc.wait())

    async def _terminate_and_wait(self, stream_name: str, proc: asyncio.subprocess.Process) -> None:
        self._processes.pop(stream_name, None)
        if proc.returncode is not None:
            await self._read_process_error(proc)
            return
        with contextlib.suppress(ProcessLookupError):
            proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(proc.wait(), timeout=2)
        await self._read_process_error(proc)

    async def _read_process_error(self, proc: asyncio.subprocess.Process) -> str:
        if proc.stderr is None:
            return ""
        try:
            data = await asyncio.wait_for(proc.stderr.read(), timeout=1)
        except (TimeoutError, ValueError):
            return ""
        text = data.decode("utf-8", errors="replace").strip()
        return text[-600:]

    async def _stop_all_recording_relays(self) -> None:
        for stream_name, (_expires_at, proc) in list(self._processes.items()):
            if is_recording_stream_name(stream_name):
                await self._terminate_and_wait(stream_name, proc)
        await self._stop_external_recording_processes()
        await self._close_zlm_recording_streams()
        await self._wait_until_recording_streams_closed()

    async def stop_recording_relays(self) -> None:
        async with self._semaphore:
            await self._stop_all_recording_relays()

    async def _stop_external_recording_processes(self) -> None:
        patterns = [
            f"{self.zlm_rtmp_push_base}/rec-",
            f"{self.zlm_rtmp_push_base}/rec_",
            "ffmpeg.*192[.]168[.]11[.]251.*/Streaming/tracks",
        ]
        for pattern in patterns:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "pkill",
                    "-f",
                    pattern,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=2)
            except (FileNotFoundError, TimeoutError, ProcessLookupError):
                pass

    async def _close_zlm_recording_streams(self) -> None:
        for stream_name in await self._recording_stream_names():
            await self._close_zlm_stream(stream_name)

    async def _close_zlm_stream(self, stream_name: str) -> None:
        params = {
            "secret": self.zlm_secret,
            "vhost": "__defaultVhost__",
            "app": "live",
            "stream": stream_name,
            "force": "1",
        }
        # 尽力而为关闭 ZLM 上的旧流，请求失败可忽略
        with contextlib.suppress(httpx.HTTPError):
            async with httpx.AsyncClient(timeout=min(self.timeout, 5)) as client:
                await client.get(f"{self.zlm_http_url}/index/api/close_streams", params=params)


async def _is_file(path: str) -> bool:
    """Check ``Path(path).is_file()`` without blocking the event loop."""
    return await asyncio.to_thread(Path(path).is_file)


def is_recording_stream_name(value) -> bool:
    return isinstance(value, str) and value.startswith(("rec-", "rec_"))
