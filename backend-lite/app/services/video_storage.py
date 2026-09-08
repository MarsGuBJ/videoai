"""文搜视频：本地视频上传到 MinIO，供分析服务按 URL 拉取。"""

import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

VIDEO_CHUNK_SIZE_BYTES = 1024 * 1024
MAX_ANALYSIS_VIDEO_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
VIDEO_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
}

_minio_client: Any = None


def _get_minio_client() -> Any:
    """惰性初始化 MinIO 客户端（本地/测试环境不要求安装 minio）。"""
    global _minio_client
    if _minio_client is None:
        from minio import Minio

        settings = get_settings()
        _minio_client = Minio(
            f"{settings.minio_endpoint}:{settings.minio_port}",
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
    return _minio_client


async def save_analysis_video(video: UploadFile) -> str:
    """上传本地视频到 MinIO 并返回其可访问 URL。

    Args:
        video: 上传文件，必须是支持的视频格式（mp4/mov/avi/mkv）。

    Returns:
        MinIO 中该视频的 HTTP URL。

    Raises:
        HTTPException: 格式不支持、超过大小上限或内容为空时 400。
    """
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 mp4、mov、avi 或 mkv 视频文件")
    temp_path = Path(tempfile.gettempdir()) / f"analysis-upload-{uuid4().hex}{suffix}"
    total_bytes = 0
    try:
        with temp_path.open("wb") as output:
            while True:
                chunk = await video.read(VIDEO_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_ANALYSIS_VIDEO_BYTES:
                    raise HTTPException(status_code=400, detail="视频文件不能超过 2 GB")
                output.write(chunk)
        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="视频文件为空")
        settings = get_settings()
        client = _get_minio_client()
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        object_name = f"recordings/uploads/{uuid4().hex}{suffix}"
        client.fput_object(
            settings.minio_bucket,
            object_name,
            str(temp_path),
            content_type=VIDEO_CONTENT_TYPES[suffix],
        )
        scheme = "https" if settings.minio_use_ssl else "http"
        return f"{scheme}://{settings.minio_endpoint}:{settings.minio_port}/{settings.minio_bucket}/{object_name}"
    finally:
        temp_path.unlink(missing_ok=True)


def _reset_minio_client_for_test() -> None:
    global _minio_client
    _minio_client = None
