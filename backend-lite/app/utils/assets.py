"""图片/快照等静态资源的存取助手。"""

import base64
import binascii
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

IMAGE_CHUNK_SIZE_BYTES = 1024 * 1024
MAX_QUERY_IMAGE_BYTES = 20 * 1024 * 1024
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def asset_path(asset_url: str, root: Path) -> Path | None:
    """将 ``/api/assets/...`` URL 安全映射为 root 下的本地路径。

    Args:
        asset_url: 资源 URL（取最后一段作为文件名）。
        root: 允许访问的根目录。

    Returns:
        root 内的解析路径；URL 为空或越出 root 时返回 None。
    """
    if not asset_url:
        return None
    filename = asset_url.rsplit("/", 1)[-1]
    path = (root / filename).resolve()
    if not str(path).startswith(str(root.resolve())):
        return None
    return path


async def save_face_photo(face_id: UUID, photo: UploadFile) -> str:
    """保存人脸照片并返回其对外 URL。

    Args:
        face_id: 人脸档案 ID，用作文件名。
        photo: 上传文件，必须是图片类型。

    Returns:
        ``/api/assets/faces/<filename>`` 形式的 URL。

    Raises:
        HTTPException: 非图片 content-type 时 400。
    """
    settings = get_settings()
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    suffix = Path(photo.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        suffix = ".jpg"
    filename = f"{face_id}{suffix}"
    path = settings.face_storage_dir / filename
    with path.open("wb") as output:
        while True:
            chunk = await photo.read(IMAGE_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            output.write(chunk)
    return f"/api/assets/faces/{filename}"


async def save_query_image(image: UploadFile) -> Path:
    """保存以图搜人的查询图片，带 20 MB 上限与空文件校验。

    Args:
        image: 上传文件，必须是图片类型。

    Returns:
        保存后的本地路径。

    Raises:
        HTTPException: 非图片、超过 20 MB 或内容为空时 400。
    """
    settings = get_settings()
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        suffix = ".jpg"
    path = settings.query_image_storage_dir / f"{uuid4()}{suffix}"
    total_bytes = 0
    with path.open("wb") as output:
        while True:
            chunk = await image.read(IMAGE_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_QUERY_IMAGE_BYTES:
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Image file must be 20 MB or smaller")
            output.write(chunk)
    if total_bytes == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Image file is empty")
    return path


async def save_review_image(image: UploadFile) -> str:
    """保存复核任务上传的图片并返回其对外 URL。

    校验规则与 save_query_image 一致：图片 content-type、20 MB 上限、非空。

    Args:
        image: 上传文件，必须是图片类型。

    Returns:
        ``/api/assets/review-images/<filename>`` 形式的 URL。

    Raises:
        HTTPException: 非图片、超过 20 MB 或内容为空时 400。
    """
    settings = get_settings()
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        suffix = ".jpg"
    filename = f"{uuid4()}{suffix}"
    path = settings.review_image_storage_dir / filename
    total_bytes = 0
    with path.open("wb") as output:
        while True:
            chunk = await image.read(IMAGE_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_QUERY_IMAGE_BYTES:
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Image file must be 20 MB or smaller")
            output.write(chunk)
    if total_bytes == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Image file is empty")
    return f"/api/assets/review-images/{filename}"


def save_snapshot(snapshot_base64: str | None) -> str | None:
    """将 base64 快照落盘并返回对外 URL；数据非法时返回 None。

    Args:
        snapshot_base64: base64（可带 data URL 前缀），可为 None。

    Returns:
        ``/api/assets/snapshots/<filename>`` URL，或 None。
    """
    if not snapshot_base64:
        return None
    data = snapshot_base64
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        return None
    if not raw:
        return None
    filename = f"{uuid4()}.jpg"
    (get_settings().snapshot_storage_dir / filename).write_bytes(raw)
    return f"/api/assets/snapshots/{filename}"


def delete_face_photo(photo_url: str) -> None:
    """删除人脸照片文件（越出存储目录的 URL 直接忽略）。

    Args:
        photo_url: ``/api/assets/faces/<filename>`` 形式的 URL。
    """
    settings = get_settings()
    filename = photo_url.rsplit("/", 1)[-1]
    path = (settings.face_storage_dir / filename).resolve()
    if str(path).startswith(str(settings.face_storage_dir.resolve())) and path.is_file():
        path.unlink()


def jpeg_data_url(frame: bytes) -> str:
    """把 JPEG 字节包装为 data URL。

    Args:
        frame: JPEG 图片字节。

    Returns:
        ``data:image/jpeg;base64,...`` 字符串。
    """
    return "data:image/jpeg;base64," + base64.b64encode(frame).decode("ascii")
