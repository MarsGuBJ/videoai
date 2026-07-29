from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import socket
import threading
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


class PreviewRelayError(RuntimeError):
    pass


class PreviewRelayTimeout(PreviewRelayError):
    pass


def preview_stream_name(stream_name: str) -> str:
    return f"preview-{stream_name}"


class ZlmPreviewClient:
    def __init__(
        self,
        base_url: str,
        secret: str,
        preview_rtmp_base: str,
        command_key: str,
        timeout_ms: int,
        opener: Callable = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.preview_rtmp_base = preview_rtmp_base.rstrip("/")
        self.command_key = command_key
        self.timeout_ms = timeout_ms
        self._opener = opener

    def start(self, stream_name: str, source_url: str) -> str:
        derived_stream = quote(preview_stream_name(stream_name), safe="")
        destination_url = f"{self.preview_rtmp_base}/{derived_stream}"
        try:
            payload = self._request(
                "/index/api/addFFmpegSource",
                {
                    "secret": self.secret,
                    "src_url": source_url,
                    "dst_url": destination_url,
                    "timeout_ms": str(self.timeout_ms),
                    "enable_hls": "0",
                    "enable_mp4": "0",
                    "ffmpeg_cmd_key": self.command_key,
                },
            )
            key = str(payload.get("data", {}).get("key", "")).strip()
            if not key:
                raise PreviewRelayError("ZLMediaKit did not return a preview relay key")
            return key
        except PreviewRelayError:
            self._cleanup_destination(destination_url)
            raise

    def stop(self, key: str) -> None:
        self._request(
            "/index/api/delFFmpegSource",
            {"secret": self.secret, "key": key},
        )

    def _cleanup_destination(self, destination_url: str) -> None:
        try:
            payload = self._request(
                "/index/api/listFFmpegSource",
                {"secret": self.secret},
            )
        except PreviewRelayError:
            logger.warning("Failed to inspect uncertain ZLMediaKit preview relay startup")
            return

        sources = payload.get("data", [])
        if not isinstance(sources, list):
            return
        for source in sources:
            if not isinstance(source, dict) or source.get("dst_url") != destination_url:
                continue
            key = str(source.get("key", "")).strip()
            if not key:
                continue
            try:
                self.stop(key)
            except PreviewRelayError:
                logger.warning("Failed to remove uncertain ZLMediaKit preview relay startup")

    def _request(self, path: str, params: dict[str, str]) -> dict:
        request = Request(
            f"{self.base_url}{path}?{urlencode(params)}",
            headers={"User-Agent": "VideoAI-Lite/1.0"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=max(1, self.timeout_ms / 1000 + 2)) as response:
                body = response.read()
        except (TimeoutError, socket.timeout) as exc:
            raise PreviewRelayTimeout("ZLMediaKit preview relay request timed out") from exc
        except (HTTPError, URLError, OSError) as exc:
            raise PreviewRelayError("ZLMediaKit preview relay request failed") from exc

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
            raise PreviewRelayError("ZLMediaKit returned an invalid preview relay response") from exc

        if not isinstance(payload, dict) or payload.get("code") != 0:
            message = str(payload.get("msg", "")) if isinstance(payload, dict) else ""
            if "timeout" in message.lower():
                raise PreviewRelayTimeout("ZLMediaKit preview relay request timed out")
            raise PreviewRelayError("ZLMediaKit rejected the preview relay request")
        return payload


@dataclass
class RelayState:
    source_url: str
    ready: threading.Event = field(default_factory=threading.Event)
    stopped: threading.Event = field(default_factory=threading.Event)
    key: str | None = None
    error: PreviewRelayError | None = None
    viewers: int = 0
    idle_timer: threading.Timer | None = None
    stopping: bool = False


class PreviewRelayManager:
    def __init__(
        self,
        client: ZlmPreviewClient,
        idle_seconds: float = 60,
        timer_factory: Callable = threading.Timer,
    ) -> None:
        self.client = client
        self.idle_seconds = idle_seconds
        self._timer_factory = timer_factory
        self._lock = threading.Lock()
        self._states: dict[str, RelayState] = {}

    def acquire(self, stream_name: str, source_url: str) -> str:
        while True:
            owner = False
            wait_for_start: threading.Event | None = None
            wait_for_stop: threading.Event | None = None
            with self._lock:
                state = self._states.get(stream_name)
                if state is None:
                    state = RelayState(source_url=source_url, viewers=1)
                    self._states[stream_name] = state
                    owner = True
                elif state.stopping:
                    wait_for_stop = state.stopped
                elif not state.ready.is_set():
                    state.viewers += 1
                    wait_for_start = state.ready
                elif state.error is not None:
                    self._states.pop(stream_name, None)
                    continue
                else:
                    if state.source_url != source_url:
                        raise PreviewRelayError("Preview relay source changed while active")
                    if state.idle_timer is not None:
                        state.idle_timer.cancel()
                        state.idle_timer = None
                    state.viewers += 1
                    return self._relay_url(stream_name)

            if wait_for_stop is not None:
                wait_for_stop.wait()
                if state.error is not None:
                    raise state.error
                continue
            if wait_for_start is not None:
                wait_for_start.wait()
                if state.error is not None:
                    raise state.error
                if state.stopping:
                    state.stopped.wait()
                    continue
                return self._relay_url(stream_name)
            if owner:
                return self._start_owned(stream_name, source_url, state)

    def release(self, stream_name: str) -> None:
        timer = None
        with self._lock:
            state = self._states.get(stream_name)
            if state is None or state.stopping or not state.ready.is_set():
                return
            state.viewers = max(0, state.viewers - 1)
            if state.viewers != 0 or state.idle_timer is not None:
                return
            timer = self._timer_factory(
                self.idle_seconds,
                lambda: self._expire(stream_name, state),
            )
            timer.daemon = True
            state.idle_timer = timer
        timer.start()

    def stop_stream(self, stream_name: str) -> None:
        wait_for_existing_stop = False
        with self._lock:
            state = self._states.get(stream_name)
            if state is None:
                return
            state.error = PreviewRelayError("Preview relay was explicitly stopped")
            if state.stopping:
                wait_for_existing_stop = True
            else:
                state.stopping = True
                if state.idle_timer is not None:
                    state.idle_timer.cancel()
                    state.idle_timer = None
        if wait_for_existing_stop:
            state.stopped.wait()
            return
        state.ready.wait()
        self._finish_stop(stream_name, state)

    def shutdown(self) -> None:
        with self._lock:
            stream_names = list(self._states)
        for stream_name in stream_names:
            self.stop_stream(stream_name)

    def viewer_count(self, stream_name: str) -> int:
        with self._lock:
            state = self._states.get(stream_name)
            return state.viewers if state is not None and not state.stopping else 0

    def _start_owned(self, stream_name: str, source_url: str, state: RelayState) -> str:
        try:
            key = self.client.start(stream_name, source_url)
        except PreviewRelayError as exc:
            with self._lock:
                state.error = exc
                if self._states.get(stream_name) is state:
                    self._states.pop(stream_name, None)
                state.ready.set()
                state.stopped.set()
            raise
        except Exception as exc:
            error = PreviewRelayError("ZLMediaKit preview relay request failed")
            with self._lock:
                state.error = error
                if self._states.get(stream_name) is state:
                    self._states.pop(stream_name, None)
                state.ready.set()
                state.stopped.set()
            raise error from exc

        with self._lock:
            state.key = key
            state.ready.set()
            stopping = state.stopping
        if stopping:
            state.stopped.wait()
            raise state.error or PreviewRelayError("Preview relay stopped during startup")
        return self._relay_url(stream_name)

    def _expire(self, stream_name: str, state: RelayState) -> None:
        with self._lock:
            current = self._states.get(stream_name)
            if current is not state or state.viewers != 0 or state.stopping:
                return
            state.stopping = True
            state.idle_timer = None
        self._finish_stop(stream_name, state)

    def _finish_stop(self, stream_name: str, state: RelayState) -> None:
        try:
            if state.key:
                self.client.stop(state.key)
        except PreviewRelayError as exc:
            logger.warning("Failed to stop ZLMediaKit preview relay for %s: %s", stream_name, exc)
        finally:
            with self._lock:
                if self._states.get(stream_name) is state:
                    self._states.pop(stream_name, None)
                state.stopped.set()

    def _relay_url(self, stream_name: str) -> str:
        derived_stream = quote(preview_stream_name(stream_name), safe="")
        return f"{self.client.base_url}/live/{derived_stream}.live.flv"
