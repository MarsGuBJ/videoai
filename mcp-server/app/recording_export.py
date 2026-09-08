"""NVR 录像导出：优先 HCNetSDK 按时间下载（非实时，快），失败时回退 RTSP 回放抓流。

远程 NVR（海康）实测行为：
- 回放地址为 ``/Streaming/tracks/{trackId}/?starttime=...&endtime=...``（尾斜杠必需，
  ``/Streaming/Channels/{id}`` 带时间参数只会返回实时流边缘）。
- ``starttime``/``endtime`` 的 ``Z`` 后缀数字按 **NVR 本地时钟**解释（不是 UTC）。
- ``endtime`` 不生效，回放不会自动停止，必须用 ffmpeg ``-t`` 截断。
- RTSP 回放吐流速度约 1x，抓流导出墙钟时间 ≈ 录像时长，仅作 SDK 不可用时的兜底（≤20 分钟）。
- SDK ``NET_DVR_GetFileByTime`` 下载不受 1x 限制，速度取决于网络带宽，为默认导出方式。
- 现场 NVR 为手动对时，可能与时区真实时间存在偏差，导出前通过
  ``/ISAPI/System/time`` 测量偏移并补偿。
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from uuid import uuid4
from xml.etree import ElementTree

import httpx

from .context import hcnetsdk_downloaders, recording_mp4_storage, settings

MAX_EXPORT_DURATION_SECONDS = 1200
# SDK 下载不按 1x 实时抓流，可承载更长时段；总上限 2 小时
MAX_SDK_EXPORT_DURATION_SECONDS = 7200
MIN_VALID_MP4_BYTES = 100 * 1024
FFMPEG_TIMEOUT_MARGIN_SECONDS = 45
REMUX_TIMEOUT_SECONDS = 120
CAPTURE_TRAILING_SECONDS = 3
NVR_TIME_PATH = "/ISAPI/System/time"
BEIJING_TZ = timezone(timedelta(hours=8))


class RecordingExportError(RuntimeError):
    """Raised when an NVR recording export fails."""


async def export_recording_mp4(track_id: str, start_time: datetime, end_time: datetime) -> dict[str, Any]:
    """Capture one NVR track's recording for a time range and upload it as MP4.

    Args:
        track_id: NVR 回放 track（如 ``201``，对应 ``/Streaming/tracks/201/``）。
        start_time: 开始时间（感知时区）。
        end_time: 结束时间（感知时区）。

    Returns:
        含 ``videoUrl``、``durationSeconds``、``trackId``、起止时间的字典。

    Raises:
        ValueError: 时长非法或超过上限。
        RecordingExportError: 抓流失败或该时段无有效录像。
    """
    duration = (end_time - start_time).total_seconds()
    if duration < 1:
        raise ValueError("endTime must be later than startTime")
    if duration > MAX_EXPORT_DURATION_SECONDS:
        raise ValueError(f"export duration must not exceed {MAX_EXPORT_DURATION_SECONDS} seconds")
    skew = await fetch_nvr_clock_skew()
    playback_url = build_track_playback_url(track_id, start_time, end_time, skew)
    started = time.monotonic()
    mp4_file = await asyncio.to_thread(capture_playback_to_mp4, playback_url, duration)
    try:
        object_name = f"recordings/exports/{track_id}/{uuid4().hex}.mp4"
        video_url = recording_mp4_storage.upload_mp4(mp4_file, object_name)
    finally:
        mp4_file.unlink(missing_ok=True)
    return {
        "videoUrl": video_url,
        "durationSeconds": int(duration),
        "trackId": track_id,
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "nvrClockSkewSeconds": int(skew),
        "exportElapsedSeconds": round(time.monotonic() - started, 1),
    }


def _with_rtsp_reason(rtsp_error: Exception | None, message: str) -> str:
    if rtsp_error is None:
        return message
    return f"rtsp export failed: {rtsp_error}; {message}"


async def export_recording_via_downloader(
    downloader: Any,
    track_id: str,
    channel: int | None,
    start_time: datetime,
    end_time: datetime,
    rtsp_error: Exception | None = None,
) -> dict[str, Any]:
    """通过给定 HCNetSDK 下载器按时间下载录像并上传 MinIO（非实时抓流，含时钟偏差补偿）。

    Args:
        downloader: ``HcNetSdkPlaybackProxy`` 实例（白名单或按摄像头 sourceUrl 缓存的设备代理）。
        track_id: 展示与对象命名用的 track（如 ``201``）。
        channel: SDK 通道号（如 ``2``）；``None`` 时用下载器默认通道。
        rtsp_error: 仅在作为 RTSP 失败兜底调用时传入，错误消息会附带 RTSP 侧原因。

    Raises:
        RecordingExportError: SDK 下载失败。
    """
    skew = await downloader.measure_clock_skew()
    shift = timedelta(seconds=skew)
    recording = downloader.build_download_recording(start_time + shift, end_time + shift, channel or None)
    started = time.monotonic()
    try:
        mp4_file = await downloader.download_mp4(recording)
    except Exception as exc:
        raise RecordingExportError(_with_rtsp_reason(rtsp_error, f"sdk download failed: {exc}")) from exc
    try:
        object_name = f"recordings/exports/{track_id}/{uuid4().hex}.mp4"
        video_url = recording_mp4_storage.upload_mp4(mp4_file, object_name)
    finally:
        mp4_file.unlink(missing_ok=True)
    return {
        "videoUrl": video_url,
        "durationSeconds": int((end_time - start_time).total_seconds()),
        "trackId": track_id,
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "nvrClockSkewSeconds": int(skew),
        "exportElapsedSeconds": round(time.monotonic() - started, 1),
        "exportMethod": "hcnetsdk_download",
    }


async def export_recording_via_sdk_download(
    track_id: str, start_time: datetime, end_time: datetime, rtsp_error: Exception | None = None
) -> dict[str, Any]:
    """通过白名单 NVR（``HIKVISION_NVR_BASE_URL`` 主机）的 HCNetSDK 下载器按时间下载录像。

    SDK 通道号由 trackId 换算（``201`` -> ``2``）；下载时间段叠加实测的 NVR 时钟偏差。
    ``rtsp_error`` 仅在作为 RTSP 失败兜底调用时传入，错误消息会附带 RTSP 侧原因。

    Raises:
        RecordingExportError: 无可用下载器、trackId 非法或 SDK 下载失败。
    """
    host = urlparse(settings.hikvision_base_url).hostname or ""
    downloader = hcnetsdk_downloaders.get(host)
    if downloader is None:
        raise RecordingExportError(
            _with_rtsp_reason(rtsp_error, f"no HCNetSDK downloader configured for {host or 'NVR'}")
        )
    try:
        channel = int(track_id.strip()) // 100
    except ValueError:
        raise RecordingExportError(
            _with_rtsp_reason(rtsp_error, f"trackId must be numeric, got: {track_id}")
        ) from None
    return await export_recording_via_downloader(downloader, track_id, channel, start_time, end_time, rtsp_error)


def build_track_playback_url(track_id: str, start_time: datetime, end_time: datetime, skew_seconds: float) -> str:
    """Build the NVR RTSP playback URL, translating to NVR-local wall-clock digits."""
    host = urlparse(settings.hikvision_base_url).hostname
    if not host:
        raise RecordingExportError("HIKVISION_NVR_BASE_URL is not configured")
    if not settings.hikvision_username or not settings.hikvision_password:
        raise RecordingExportError("Hikvision NVR credentials are not configured")
    user = quote(settings.hikvision_username, safe="")
    password = quote(settings.hikvision_password, safe="")
    start_digits = to_nvr_wall_digits(start_time, skew_seconds)
    end_digits = to_nvr_wall_digits(end_time, skew_seconds)
    return (
        f"rtsp://{user}:{password}@{host}:554"
        f"/Streaming/tracks/{track_id}/?starttime={start_digits}&endtime={end_digits}"
    )


def to_nvr_wall_digits(value: datetime, skew_seconds: float) -> str:
    """Format a datetime as NVR playback time digits (NVR-local wall clock + 'Z').

    NVR 回放把 ``Z`` 后缀数字按设备本地（东八区）时钟解释，因此先转为北京时间墙钟，
    再叠加实测时钟偏差（NVR 时间减服务器时间），最后直接取数字部分。
    """
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    wall = value.astimezone(BEIJING_TZ) + timedelta(seconds=skew_seconds)
    return wall.strftime("%Y%m%dT%H%M%SZ")


async def fetch_nvr_clock_skew() -> float:
    """Return NVR clock offset in seconds (NVR time minus server time); 0 on failure."""
    base_url = settings.hikvision_base_url.rstrip("/")
    if not base_url or not settings.hikvision_username:
        return 0.0
    try:
        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(settings.hikvision_username, settings.hikvision_password),
            timeout=settings.request_timeout_seconds,
        ) as client:
            response = await client.get(f"{base_url}{NVR_TIME_PATH}")
            response.raise_for_status()
        local_time = ElementTree.fromstring(response.text).findtext(".//{*}localTime")  # noqa: S314  # XML 来自内网受信 NVR
        if not local_time:
            return 0.0
        nvr_now = datetime.fromisoformat(local_time.strip())
        return nvr_now.astimezone(timezone.utc).timestamp() - datetime.now(timezone.utc).timestamp()
    except (httpx.HTTPError, ValueError, ElementTree.ParseError):
        return 0.0


def capture_playback_to_mp4(playback_url: str, duration_seconds: float) -> Path:
    """Capture the RTSP playback stream for the given duration into an MP4 file.

    两段式：先抓流为 MPEG-TS（可安全强杀），再 remux 为 faststart MP4。
    NVR 在录像边界停发数据后 ffmpeg 不会自行退出，因此抓流阶段设墙钟上限，
    超时时杀掉进程并继续使用已抓到的部分。
    """
    work_dir = Path(tempfile.mkdtemp(prefix="recording-export-"))
    ts_file = work_dir / "capture.ts"
    mp4_file = work_dir / "export.mp4"
    timeout = duration_seconds + FFMPEG_TIMEOUT_MARGIN_SECONDS
    try:
        # ffmpeg 可执行文件由部署环境 PATH 提供，URL 由内部构造
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-i",
                playback_url,
                "-t",
                str(int(duration_seconds) + CAPTURE_TRAILING_SECONDS),
                "-an",
                "-c:v",
                "copy",
                "-f",
                "mpegts",
                "-y",
                str(ts_file),
            ],
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or f"ffmpeg exited with code {result.returncode}"
            raise RecordingExportError(f"ffmpeg capture failed: {detail}")
    except subprocess.TimeoutExpired:
        # NVR 停发后进程不死：用已抓到的部分继续（内容不足会在下面被判为无录像）
        pass
    try:
        if not ts_file.is_file() or ts_file.stat().st_size < MIN_VALID_MP4_BYTES:
            raise ValueError("该时段无可用录像")
        remux = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(ts_file),
                "-an",
                "-c:v",
                "copy",
                "-movflags",
                "+faststart",
                "-y",
                str(mp4_file),
            ],
            text=True,
            capture_output=True,
            timeout=REMUX_TIMEOUT_SECONDS,
        )
        if remux.returncode != 0:
            detail = remux.stderr.strip() or f"ffmpeg exited with code {remux.returncode}"
            raise RecordingExportError(f"ffmpeg remux to MP4 failed: {detail}")
        if not is_valid_mp4(mp4_file):
            raise ValueError("该时段无可用录像")
        final_file = Path(tempfile.gettempdir()) / f"recording-export-{uuid4().hex}.mp4"
        shutil.move(str(mp4_file), final_file)
        return final_file
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def is_valid_mp4(mp4_file: Path) -> bool:
    """Check the captured file exists, has size and a positive duration."""
    if not mp4_file.is_file() or mp4_file.stat().st_size < MIN_VALID_MP4_BYTES:
        return False
    # ffprobe 可执行文件由部署环境 PATH 提供
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(mp4_file),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return False
    import json

    try:
        duration = float(json.loads(result.stdout).get("format", {}).get("duration") or 0)
    except (ValueError, TypeError):
        return False
    return duration >= 1
