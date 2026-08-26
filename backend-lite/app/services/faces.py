"""人脸档案与人脸向量的持久化、加载与匹配计算。"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import UUID, uuid4

from fastapi import HTTPException

from app import state
from app.core.config import get_settings
from app.schemas.face import FaceProfileResponse
from app.utils.assets import ALLOWED_IMAGE_SUFFIXES, asset_path

logger = logging.getLogger(__name__)

FACE_EXTRACT_TIMEOUT_SECONDS = 30


def require_face(face_id: UUID) -> FaceProfileResponse:
    """按 ID 取人脸档案，不存在则 404。

    Args:
        face_id: 人脸档案 ID。

    Returns:
        对应的人脸档案。

    Raises:
        HTTPException: 档案不存在时 404。
    """
    face = state.faces_store.get(face_id)
    if not face:
        raise HTTPException(status_code=404, detail="Face profile not found")
    return face


def load_faces_from_disk() -> None:
    """启动时从 faces.json 加载档案，并从残留照片文件恢复缺失记录。"""
    settings = get_settings()
    state.faces_store.clear()
    if settings.face_metadata_file.is_file():
        try:
            raw_faces = json.loads(settings.face_metadata_file.read_text(encoding="utf-8"))
            for raw in raw_faces:
                face = FaceProfileResponse(**raw)
                photo = asset_path(face.photoUrl, settings.face_storage_dir)
                if photo and photo.is_file():
                    state.faces_store[face.id] = face
        except (OSError, TypeError, ValueError) as exc:
            logger.error("failed to load face metadata: %s", exc)
    recovered = False
    for path in sorted(settings.face_storage_dir.iterdir()):
        if path.name in {".gitkeep", settings.face_metadata_file.name} or not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            continue
        try:
            face_id = UUID(path.stem)
        except ValueError:
            face_id = uuid4()
            new_path = path.with_name(f"{face_id}{path.suffix.lower()}")
            path.rename(new_path)
            path = new_path
        if face_id in state.faces_store:
            continue
        now = datetime.now(timezone.utc)
        state.faces_store[face_id] = FaceProfileResponse(
            id=face_id,
            name=f"未命名人脸-{str(face_id)[:8]}",
            description="从已保存照片恢复，请编辑姓名和描述",
            photoUrl=f"/api/assets/faces/{path.name}",
            createdAt=now,
            updatedAt=now,
        )
        recovered = True
    if recovered or (state.faces_store and not settings.face_metadata_file.is_file()):
        persist_faces()


def persist_faces() -> None:
    """把当前人脸档案快照写入 faces.json。"""
    settings = get_settings()
    data = [
        json.loads(face.model_dump_json())
        for face in sorted(state.faces_store.values(), key=lambda item: item.createdAt)
    ]
    settings.face_metadata_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_face_embeddings() -> None:
    """启动时加载人脸向量缓存，并补齐缺失档案的向量。"""
    settings = get_settings()
    state.face_embeddings.clear()
    if settings.face_embeddings_file.is_file():
        try:
            raw = json.loads(settings.face_embeddings_file.read_text(encoding="utf-8"))
            for face_id, embedding in raw.items():
                try:
                    parsed_id = UUID(face_id)
                except ValueError:
                    continue
                if parsed_id in state.faces_store and isinstance(embedding, list):
                    state.face_embeddings[parsed_id] = [float(value) for value in embedding]
        except (OSError, TypeError, ValueError) as exc:
            logger.error("failed to load face embeddings: %s", exc)
    changed = False
    for face in state.faces_store.values():
        if face.id not in state.face_embeddings:
            changed = refresh_face_embedding(face) or changed
    if changed:
        persist_face_embeddings()


def persist_face_embeddings() -> None:
    """把当前人脸向量快照写入 face_embeddings.json。"""
    settings = get_settings()
    data = {
        str(face_id): embedding for face_id, embedding in state.face_embeddings.items() if face_id in state.faces_store
    }
    settings.face_embeddings_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def refresh_face_embedding(face: FaceProfileResponse) -> bool:
    """重新提取指定档案的人脸向量。

    Args:
        face: 目标人脸档案。

    Returns:
        提取成功返回 True；照片缺失或提取失败时清除旧向量并返回 False。
    """
    settings = get_settings()
    path = asset_path(face.photoUrl, settings.face_storage_dir)
    if path is None or not path.is_file():
        state.face_embeddings.pop(face.id, None)
        persist_face_embeddings()
        return False
    try:
        embedding = extract_face_embedding(path)
    except (RuntimeError, OSError) as exc:
        state.face_embeddings.pop(face.id, None)
        persist_face_embeddings()
        logger.error("failed to extract embedding for %s: %s", face.name, exc)
        return False
    state.face_embeddings[face.id] = embedding
    persist_face_embeddings()
    return True


def extract_face_embedding(path: Path) -> list[float]:
    """调用 worker 的 /v1/faces/extract 提取人脸向量。

    Args:
        path: 本地照片路径。

    Returns:
        浮点向量列表。

    Raises:
        RuntimeError: worker 不可达、返回错误或向量为空。
    """
    worker_url = get_settings().worker_url
    with path.open("rb") as photo:
        boundary = "----VideoAIBoundary"
        body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                "Content-Type: image/jpeg\r\n\r\n"
            ).encode()
            + photo.read()
            + f"\r\n--{boundary}--\r\n".encode()
        )
    request = UrlRequest(  # noqa: S310  # 内网固定 worker 地址
        f"{worker_url}/v1/faces/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=FACE_EXTRACT_TIMEOUT_SECONDS) as response:  # noqa: S310  # 内网固定 worker 地址
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise RuntimeError(f"worker extract failed: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"worker is not reachable at {worker_url}: {exc.reason}") from exc
    embedding = payload.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("worker returned empty embedding")
    return [float(value) for value in embedding]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两个等长向量的余弦相似度。

    Args:
        left: 向量 A。
        right: 向量 B。

    Returns:
        相似度；长度不一致或零范数时返回 0.0。
    """
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right, strict=True):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    denominator = math.sqrt(left_norm) * math.sqrt(right_norm)
    if denominator <= 0:
        return 0.0
    return dot / denominator
