"""复核任务的视频上传校验与抽帧（事件判断弹窗的视频判定链路）。"""

import logging
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MAX_REVIEW_VIDEO_BYTES = 100 * 1024 * 1024  # 100 MB
VIDEO_FRAME_TIMEOUT_SECONDS = 60
DEFAULT_FRAME_COUNT = 4
FRAME_WIDTH = 640


def validate_video_upload(video: UploadFile, size: int) -> None:
    """校验复核任务上传的视频：content-type、100 MB 上限、非空。

    Args:
        video: 上传文件。
        size: 已读取的文件字节数。

    Raises:
        HTTPException: 非视频、超过 100 MB 或内容为空时 400。
    """
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="仅支持视频文件")
    if size > MAX_REVIEW_VIDEO_BYTES:
        raise HTTPException(status_code=400, detail="视频大小不能超过 100MB")
    if size == 0:
        raise HTTPException(status_code=400, detail="视频内容为空")


def _run_ffmpeg_frames(video_path: Path, output_pattern: Path, vf: str, count: int, seek: float | None) -> list[bytes]:
    """执行一次 ffmpeg 抽帧并读取产物；失败/无输出返回空列表。

    Args:
        video_path: 视频临时文件路径。
        output_pattern: 输出帧命名模式（如 f-%02d.jpg）。
        vf: 视频过滤器表达式。
        count: 最多抽取帧数。
        seek: 可选起跳秒数（None 不起跳）。

    Returns:
        按文件名排序的 JPEG 帧字节列表。
    """
    command = [get_settings().ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y"]
    if seek is not None:
        command += ["-ss", f"{seek:.3f}"]
    command += [
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-frames:v",
        str(count),
        "-q:v",
        "3",
        str(output_pattern),
    ]
    try:
        subprocess.run(  # noqa: S603  # 参数列表固定，输入为服务端保存的临时文件
            command,
            capture_output=True,
            timeout=VIDEO_FRAME_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("review video frame extraction failed: %s", exc)
        return []
    return [path.read_bytes() for path in sorted(output_pattern.parent.glob("f-*.jpg"))]


def extract_video_frames(video_bytes: bytes, filename: str = "", count: int = DEFAULT_FRAME_COUNT) -> list[bytes]:
    """从视频字节中按时间抽取至多 count 帧 JPEG（每 2 秒一帧，缩放到 640 宽）。

    极短视频 fps 抽帧可能无产出，回退为 0 秒处首帧。

    Args:
        video_bytes: 视频文件字节。
        filename: 原始文件名（用于推断临时文件后缀，缺省 .mp4）。
        count: 最多抽取帧数。

    Returns:
        JPEG 帧字节列表（至少一帧）。

    Raises:
        HTTPException: 一帧都抽不出来时 400（视频损坏或不含视频流）。
    """
    suffix = Path(filename or "").suffix.lower() or ".mp4"
    with tempfile.TemporaryDirectory(prefix="videoai-review-") as tmp:
        video_path = Path(tmp) / f"input{suffix}"
        video_path.write_bytes(video_bytes)
        output_pattern = Path(tmp) / "f-%02d.jpg"
        frames = _run_ffmpeg_frames(video_path, output_pattern, f"fps=1/2,scale={FRAME_WIDTH}:-2", count, None)
        if not frames:
            frames = _run_ffmpeg_frames(video_path, output_pattern, f"scale={FRAME_WIDTH}:-2", 1, 0.0)
    if not frames:
        raise HTTPException(status_code=400, detail="视频抽帧失败，请确认视频文件有效")
    return frames


def save_review_frame(frame: bytes) -> str:
    """把抽帧 JPEG 落盘到复核图片目录，返回对外 URL（视频任务的列表/详情缩略图）。

    Args:
        frame: JPEG 图片字节。

    Returns:
        ``/api/assets/review-images/<filename>`` 形式的 URL。
    """
    filename = f"{uuid4()}.jpg"
    path = get_settings().review_image_storage_dir / filename
    path.write_bytes(frame)
    return f"/api/assets/review-images/{filename}"
