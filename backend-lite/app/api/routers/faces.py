"""人脸档案管理与人脸/快照静态资源路由。"""

import base64
import binascii
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import state
from app.core.config import get_settings
from app.schemas.face import FaceProfileResponse, FaceUploadRequest
from app.services.faces import persist_face_embeddings, persist_faces, refresh_face_embedding, require_face
from app.utils.assets import delete_face_photo, save_face_photo

router = APIRouter()


@router.get("/api/faces", response_model=list[FaceProfileResponse])
def faces() -> list[FaceProfileResponse]:
    """按创建时间倒序返回全部人脸档案。"""
    return sorted(state.faces_store.values(), key=lambda item: item.createdAt, reverse=True)


@router.post("/api/faces", response_model=FaceProfileResponse)
async def create_face(
    name: str = Form(...),  # noqa: B008  # FastAPI Form 依赖注入惯例
    description: str = Form(""),  # noqa: B008
    photo: UploadFile = File(...),  # noqa: B008
) -> FaceProfileResponse:
    """上传照片创建人脸档案，并异步提取向量。"""
    face_id = uuid4()
    now = datetime.now(timezone.utc)
    photo_url = await save_face_photo(face_id, photo)
    face = FaceProfileResponse(
        id=face_id,
        name=name,
        description=description or None,
        photoUrl=photo_url,
        createdAt=now,
        updatedAt=now,
    )
    state.faces_store[face_id] = face
    refresh_face_embedding(face)
    persist_faces()
    return face


@router.patch("/api/faces/{face_id}", response_model=FaceProfileResponse)
async def update_face(
    face_id: UUID,
    name: str = Form(...),  # noqa: B008
    description: str = Form(""),  # noqa: B008
    photo: UploadFile | None = File(None),  # noqa: B008
) -> FaceProfileResponse:
    """更新人脸档案；可选替换照片并刷新向量。"""
    face = require_face(face_id)
    photo_url = face.photoUrl
    if photo and photo.filename:
        delete_face_photo(photo_url)
        photo_url = await save_face_photo(face_id, photo)
    updated = face.model_copy(
        update={
            "name": name,
            "description": description or None,
            "photoUrl": photo_url,
            "updatedAt": datetime.now(timezone.utc),
        }
    )
    state.faces_store[face_id] = updated
    refresh_face_embedding(updated)
    persist_faces()
    return updated


@router.delete("/api/faces/{face_id}")
def delete_face(face_id: UUID) -> dict:
    """删除人脸档案及其照片与向量；不存在时同样返回空对象。"""
    face = state.faces_store.pop(face_id, None)
    if face:
        delete_face_photo(face.photoUrl)
        state.face_embeddings.pop(face_id, None)
        persist_face_embeddings()
        persist_faces()
    return {}


@router.post("/api/faces/upload-base64")
def upload_face_base64(request: FaceUploadRequest) -> dict:
    """用 base64 照片整体替换人脸库（仅保留一个档案）。"""
    if not request.imageBase64:
        raise HTTPException(status_code=400, detail="imageBase64 is required")
    data = request.imageBase64
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid base64 image data") from exc
    if not raw:
        raise HTTPException(status_code=400, detail="empty image data")

    for face in list(state.faces_store.values()):
        delete_face_photo(face.photoUrl)
        state.face_embeddings.pop(face.id, None)
        state.faces_store.pop(face.id, None)

    face_id = uuid4()
    now = datetime.now(timezone.utc)
    filename = f"{face_id}.jpg"
    path = get_settings().face_storage_dir / filename
    path.write_bytes(raw)
    photo_url = f"/api/assets/faces/{filename}"
    face = FaceProfileResponse(
        id=face_id,
        name=request.name or "人脸库照片",
        description=None,
        photoUrl=photo_url,
        createdAt=now,
        updatedAt=now,
    )
    state.faces_store[face_id] = face
    refresh_face_embedding(face)
    persist_faces()
    return {"faceId": str(face_id)}


@router.get("/api/assets/faces/{filename}")
def face_asset(filename: str) -> FileResponse:
    """返回人脸照片文件（带目录穿越防护）。"""
    face_storage_dir = get_settings().face_storage_dir
    path = (face_storage_dir / filename).resolve()
    if not str(path).startswith(str(face_storage_dir.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="Face photo not found")
    return FileResponse(path)


@router.get("/api/assets/snapshots/{filename}")
def snapshot_asset(filename: str) -> FileResponse:
    """返回事件快照文件（带目录穿越防护）。"""
    snapshot_storage_dir = get_settings().snapshot_storage_dir
    path = (snapshot_storage_dir / filename).resolve()
    if not str(path).startswith(str(snapshot_storage_dir.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return FileResponse(path)
