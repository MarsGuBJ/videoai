"""MP4 浏览器兼容处理：HEVC 源转码 H.264，其它编码直通。

现场 NVR/CVR 录像多为 smart265/HEVC；导出的 MP4 若只做 ``-c:v copy``
remux，无 HEVC 解码能力的浏览器（Chrome 等）无法播放。录像导出路径统一
先 ffprobe 探测源编码，HEVC 时转码 libx264，其余编码（H.264）原码直通。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HEVC_CODECS = ("hevc", "h265")


def probe_video_codec(video_file: Path) -> str:
    """Return the first video stream codec name (lowercase); empty string on failure."""
    # ffprobe 可执行文件由部署环境 PATH 提供
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "json",
            str(video_file),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return ""
    try:
        streams = json.loads(result.stdout).get("streams") or []
    except ValueError:
        return ""
    if not streams:
        return ""
    return str(streams[0].get("codec_name") or "").lower()


def h264_compatible_video_args(codec: str) -> list[str]:
    """ffmpeg 视频输出参数：HEVC 转码 H.264（浏览器可播），其它编码原码直通。"""
    if codec in HEVC_CODECS:
        return [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "50",
        ]
    return ["-c:v", "copy"]


def ensure_browser_compatible_mp4(mp4_file: Path) -> Path:
    """HEVC 编码的 MP4 原位转码为 H.264；其它编码原样返回。

    Raises:
        RuntimeError: ffmpeg 转码失败。
    """
    if probe_video_codec(mp4_file) not in HEVC_CODECS:
        return mp4_file
    transcoded = mp4_file.with_name(f"{mp4_file.stem}.h264.mp4")
    # ffmpeg 可执行文件由部署环境 PATH 提供，参数均为内部构造
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(mp4_file),
            "-an",
        ]
        + h264_compatible_video_args("hevc")
        + ["-movflags", "+faststart", str(transcoded)],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        transcoded.unlink(missing_ok=True)
        detail = result.stderr.strip() or f"ffmpeg exited with code {result.returncode}"
        raise RuntimeError(f"ffmpeg transcode to H.264 failed: {detail}")
    transcoded.replace(mp4_file)
    return mp4_file
