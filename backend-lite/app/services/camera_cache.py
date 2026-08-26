"""In-memory cache of the camera list pulled from the Java media backend.

The camera CRUD/streaming APIs live in the Java service now. backend-lite
still needs read access to camera data (worker stream reconciliation, face
scanning, event area lookup), so a daemon thread refreshes a local snapshot
every few seconds. Entries are stored as schemas.camera.CameraResponse
instances so existing read sites keep working unchanged.
"""

import logging
import threading
from uuid import UUID

import requests

from app.core.config import get_settings
from app.schemas.camera import CameraResponse

logger = logging.getLogger(__name__)

_settings = get_settings()
MEDIA_BACKEND_URL = _settings.media_backend_url
REFRESH_INTERVAL_SECONDS = _settings.camera_cache_refresh_interval_seconds
REQUEST_TIMEOUT_SECONDS = _settings.camera_cache_timeout_seconds

_data_lock = threading.Lock()
_thread_lock = threading.Lock()
_cameras: dict[str, CameraResponse] = {}
_stop_event = threading.Event()
_thread: threading.Thread | None = None


def _parse_camera(raw: dict) -> CameraResponse:
    return CameraResponse(**raw)


def refresh() -> bool:
    """Fetch the full camera list once. Returns True when the cache was updated."""
    try:
        response = requests.get(f"{MEDIA_BACKEND_URL}/api/cameras", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("camera cache refresh failed, keeping previous data: %s", exc)
        return False
    if not isinstance(payload, list):
        logger.warning("camera cache refresh returned a non-list payload, keeping previous data")
        return False
    parsed: dict[str, CameraResponse] = {}
    for raw in payload:
        try:
            camera = _parse_camera(raw)
        except (TypeError, ValueError) as exc:  # pydantic ValidationError 属于 ValueError
            logger.warning("camera cache skipped a malformed camera entry: %s", exc)
            continue
        parsed[str(camera.id)] = camera
    with _data_lock:
        _cameras.clear()
        _cameras.update(parsed)
    return True


def _loop() -> None:
    while not _stop_event.is_set():
        refresh()
        _stop_event.wait(REFRESH_INTERVAL_SECONDS)


def start() -> None:
    """Start the background refresh thread. Idempotent."""
    global _thread
    with _thread_lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop_event.clear()
        _thread = threading.Thread(target=_loop, name="camera-cache-refresh", daemon=True)
        _thread.start()


def stop() -> None:
    """Stop the background refresh thread and wait for it to exit."""
    global _thread
    _stop_event.set()
    with _thread_lock:
        thread = _thread
        _thread = None
    if thread is not None and thread.is_alive():
        thread.join(timeout=2)


def all() -> list[CameraResponse]:  # noqa: A001  # 与原模块公共 API 名保持一致（兼容壳 re-export）
    """Return a snapshot list of all cached cameras."""
    with _data_lock:
        return list(_cameras.values())


def get(camera_id: UUID | str) -> CameraResponse | None:
    """Return the cached camera by id, or None when absent."""
    with _data_lock:
        return _cameras.get(str(camera_id))
