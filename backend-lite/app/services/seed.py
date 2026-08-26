"""启动种子数据：默认模型注册表与演示人脸档案。"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app import state
from app.core.config import PROJECT_ROOT, get_settings
from app.schemas.face import FaceProfileResponse
from app.schemas.model import ModelResponse
from app.services.faces import persist_faces

logger = logging.getLogger(__name__)


def seed_model_registry() -> None:
    """登记内置人脸模型与模型仓库目录中的其他模型（幂等）。"""
    now = datetime.now(timezone.utc)
    defaults = [
        (
            UUID("00000000-0000-0000-0000-000000000101"),
            "scrfd_10g",
            "SCRFD-10GF",
            "FACE_DETECTION",
            "InsightFace SCRFD-10GF face detector and 5-point landmark model",
        ),
        (
            UUID("00000000-0000-0000-0000-000000000102"),
            "arcface_r50",
            "ArcFace R50",
            "FACE_RECOGNITION",
            "InsightFace ArcFace R50 face embedding model",
        ),
        (
            UUID("00000000-0000-0000-0000-000000000103"),
            "arcface_mbf",
            "ArcFace MobileFaceNet",
            "FACE_RECOGNITION",
            "InsightFace buffalo_s MobileFaceNet embedding model, w600k_mbf.onnx, about 13 MB",
        ),
    ]
    for model_id, name, display_name, model_type, description in defaults:
        if name in state.model_registry:
            continue
        state.model_registry[name] = ModelResponse(
            id=model_id,
            name=name,
            displayName=display_name,
            repositoryPath=f"/models/{name}",
            modelType=model_type,
            description=description,
            state="UNKNOWN",
            createdAt=now,
            updatedAt=now,
        )

    repository = get_settings().triton_model_repository
    if repository.is_dir():
        for path in sorted(repository.iterdir()):
            if not path.is_dir() or path.name in state.model_registry:
                continue
            state.model_registry[path.name] = ModelResponse(
                id=uuid4(),
                name=path.name,
                displayName=path.name,
                repositoryPath=f"/models/{path.name}",
                modelType="OTHER",
                description=None,
                state="UNKNOWN",
                createdAt=now,
                updatedAt=now,
            )


def seed_face_profiles() -> None:
    """人脸库为空时，用项目根目录 R-C.jpg 注册演示档案（幂等）。"""
    if state.faces_store:
        return
    src = PROJECT_ROOT / "R-C.jpg"
    if not src.is_file():
        logger.info("seed: skip face profiles, R-C.jpg not found at %s", src)
        return
    face_id = uuid4()
    filename = f"{face_id}.jpg"
    dst = get_settings().face_storage_dir / filename
    try:
        dst.write_bytes(src.read_bytes())
    except OSError as exc:
        logger.error("seed: failed to copy %s -> %s: %s", src, dst, exc)
        return
    now = datetime.now(timezone.utc)
    face = FaceProfileResponse(
        id=face_id,
        name="测试人员-小美",
        description="项目根目录 R-C.jpg，用于布控任务测试",
        photoUrl=f"/api/assets/faces/{filename}",
        createdAt=now,
        updatedAt=now,
    )
    state.faces_store[face_id] = face
    persist_faces()
    logger.info("seed: registered face profile 测试人员-小美 (%s)", face_id)
