"""算法管理路由：引擎清单、算法 CRUD、版本安装与切换。"""

from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.algorithm import (
    AlgorithmResponse,
    AlgorithmUpdateRequest,
    AlgorithmVersionResponse,
    EngineTypeInfo,
)
from app.services import algorithms as algorithm_service

router = APIRouter()


@router.get("/api/algorithm-engines", response_model=list[EngineTypeInfo])
def list_algorithm_engines() -> list[EngineTypeInfo]:
    """返回支持的算法引擎清单（含必需/可选文件）。"""
    return algorithm_service.list_engine_types()


@router.get("/api/algorithms", response_model=list[AlgorithmResponse])
def list_algorithms() -> list[AlgorithmResponse]:
    """按创建时间倒序返回全部算法。"""
    return algorithm_service.list_algorithms()


@router.post("/api/algorithms", response_model=AlgorithmResponse)
def create_algorithm(
    name: str = Form(...),  # noqa: B008  # FastAPI Form 依赖注入惯例
    code: str = Form(...),  # noqa: B008
    engine_type: str = Form(..., alias="engineType"),  # noqa: B008
    version: str = Form(...),  # noqa: B008
    scene: str | None = Form(None),  # noqa: B008
    owner: str | None = Form(None),  # noqa: B008
    description: str | None = Form(None),  # noqa: B008
    version_name: str | None = Form(None, alias="versionName"),  # noqa: B008
    notes: str | None = Form(None),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
) -> AlgorithmResponse:
    """创建算法并安装首个版本（multipart 上传 zip）。"""
    record = algorithm_service.create_algorithm(
        name=name,
        code=code,
        engine_type=engine_type,
        version=version,
        scene=scene,
        owner=owner,
        description=description,
        version_name=version_name,
        notes=notes,
        upload=file,
    )
    return algorithm_service.algorithm_response(record)


@router.patch("/api/algorithms/{algorithm_id}", response_model=AlgorithmResponse)
def update_algorithm(algorithm_id: UUID, request: AlgorithmUpdateRequest) -> AlgorithmResponse:
    """部分更新算法字段（名称/场景/负责人/描述/状态）。"""
    record = algorithm_service.require_algorithm(algorithm_id)
    updated = algorithm_service.update_algorithm(record, request)
    return algorithm_service.algorithm_response(updated)


@router.get("/api/algorithms/{algorithm_id}/versions", response_model=list[AlgorithmVersionResponse])
def list_algorithm_versions(algorithm_id: UUID) -> list[AlgorithmVersionResponse]:
    """按创建时间倒序返回算法的版本列表（active 标记当前版本）。"""
    return algorithm_service.list_versions(algorithm_service.require_algorithm(algorithm_id))


@router.post("/api/algorithms/{algorithm_id}/versions", response_model=AlgorithmVersionResponse)
def add_algorithm_version(
    algorithm_id: UUID,
    version: str = Form(...),  # noqa: B008
    version_name: str | None = Form(None, alias="versionName"),  # noqa: B008
    notes: str | None = Form(None),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
) -> AlgorithmVersionResponse:
    """备份当前版本后安装新版本，并切换为当前版本。"""
    record = algorithm_service.require_algorithm(algorithm_id)
    version_response = algorithm_service.add_version(
        record, version=version, version_name=version_name, notes=notes, upload=file
    )
    return version_response.model_copy(update={"active": True})


@router.post("/api/algorithms/{algorithm_id}/versions/{version_id}/activate", response_model=AlgorithmVersionResponse)
def activate_algorithm_version(algorithm_id: UUID, version_id: UUID) -> AlgorithmVersionResponse:
    """备份当前版本后把 current_version 指针切换到指定版本。"""
    record = algorithm_service.require_algorithm(algorithm_id)
    target = algorithm_service.activate_version(record, version_id)
    return target.model_copy(update={"active": True})
