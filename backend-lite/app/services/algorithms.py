"""算法管理：引擎清单、zip 安装校验、版本备份与内存态/数据库持久化。

内存态（state.algorithms_store）为 API 真源，数据库写入与布控任务一致
采用尽力持久化（失败仅记录日志）。安装布局：
storage/algorithms/<code>/<version>/ 保留 zip 内目录结构
（引擎 py 与 onnx 必须在根级，引擎依赖的 src/ 包原样保留）；
加版本/切换版本前把当前版本目录整体备份到
storage/algorithms/<code>/.backup/<旧version>-<UTC时间戳>/。
"""

import logging
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.algorithm import AlgorithmORM, AlgorithmVersionORM
from app.schemas.algorithm import (
    AlgorithmRecord,
    AlgorithmResponse,
    AlgorithmUpdateRequest,
    AlgorithmVersionResponse,
    EngineTypeInfo,
)

logger = logging.getLogger(__name__)

ALGORITHM_STATUS_RUNNING = "RUNNING"
ALGORITHM_STATUS_DISABLED = "DISABLED"
VERSION_STATUS_READY = "READY"
VERSION_STATUS_MISSING_FILES = "MISSING_FILES"

# 引擎清单：必需文件须位于 zip 根级（允许带一层包裹目录，安装时自动剥离），
# 引擎依赖的 src/ 包等子目录原样保留供 worker 动态加载；
# smoke 的 onnx 为可选文件，缺失时版本状态记为 MISSING_FILES，仍允许安装。
ENGINE_TYPES: dict[str, EngineTypeInfo] = {
    "face": EngineTypeInfo(
        engineType="face",
        label="人脸检测识别",
        requiredFiles=["face_engine.py", "retinaface_mobilenet0.25.onnx", "arcface_finetune.onnx"],
        optionalFiles=[],
        description="RetinaFace 检测 + ArcFace 识别的人脸算法包",
    ),
    "head": EngineTypeInfo(
        engineType="head",
        label="人头检测",
        requiredFiles=["head_engine.py", "models.onnx"],
        optionalFiles=[],
        description="人头检测算法包（单 onnx 模型）",
    ),
    "helmet": EngineTypeInfo(
        engineType="helmet",
        label="安全帽检测",
        requiredFiles=["helmet_engine.py", "helmet_v6.onnx"],
        optionalFiles=[],
        description="安全帽佩戴检测算法包",
    ),
    "kpt": EngineTypeInfo(
        engineType="kpt",
        label="人体关键点",
        requiredFiles=["kpt_engine.py", "yolov8.onnx", "dark_hrnet.onnx"],
        optionalFiles=[],
        description="人体关键点检测算法包（YOLOv8 + Dark HRNet）",
    ),
    "smoke": EngineTypeInfo(
        engineType="smoke",
        label="抽烟识别",
        requiredFiles=["smoke_engine.py"],
        optionalFiles=["yolov26_1126.onnx"],
        description="抽烟行为识别算法包；onnx 模型可选，缺失时按 MISSING_FILES 安装",
    ),
}


def list_engine_types() -> list[EngineTypeInfo]:
    """返回支持的算法引擎清单。"""
    return list(ENGINE_TYPES.values())


def current_version_of(record: AlgorithmRecord) -> AlgorithmVersionResponse | None:
    """返回当前版本记录；未设置或版本不存在时返回 None。

    Args:
        record: 算法内存记录。

    Returns:
        当前版本，或 None。
    """
    if record.currentVersion is None:
        return None
    for item in record.versions.values():
        if item.version == record.currentVersion:
            return item
    return None


def algorithm_response(record: AlgorithmRecord) -> AlgorithmResponse:
    """把内存记录转为对外响应（补齐 versionCount/当前版本状态等派生字段）。

    Args:
        record: 算法内存记录。

    Returns:
        对外算法响应。
    """
    engine = ENGINE_TYPES.get(record.engineType)
    current = current_version_of(record)
    return AlgorithmResponse(
        id=record.id,
        name=record.name,
        code=record.code,
        engineType=record.engineType,
        engineLabel=engine.label if engine else record.engineType,
        scene=record.scene,
        status=record.status,
        owner=record.owner,
        description=record.description,
        currentVersion=record.currentVersion,
        versionCount=len(record.versions),
        currentVersionStatus=current.status if current else None,
        missingFiles=list(current.missingFiles) if current else [],
        createdAt=record.createdAt,
        updatedAt=record.updatedAt,
    )


def list_algorithms() -> list[AlgorithmResponse]:
    """按创建时间倒序返回全部算法。"""
    records = sorted(state.algorithms_store.values(), key=lambda item: item.createdAt, reverse=True)
    return [algorithm_response(item) for item in records]


def require_algorithm(algorithm_id: UUID) -> AlgorithmRecord:
    """按 ID 取算法，不存在则 404。

    Args:
        algorithm_id: 算法 ID。

    Returns:
        算法内存记录。

    Raises:
        HTTPException: 算法不存在时 404。
    """
    record = state.algorithms_store.get(algorithm_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    return record


def require_bindable_algorithm(algorithm_id: UUID) -> AlgorithmRecord:
    """校验算法可被布控任务绑定：存在、未停用、当前版本 READY。

    Args:
        algorithm_id: 算法 ID。

    Returns:
        算法内存记录。

    Raises:
        HTTPException: 任一校验失败时 400。
    """
    record = state.algorithms_store.get(algorithm_id)
    if record is None:
        raise HTTPException(status_code=400, detail="Algorithm not found")
    if record.status == ALGORITHM_STATUS_DISABLED:
        raise HTTPException(status_code=400, detail="Algorithm is disabled")
    current = current_version_of(record)
    if current is None:
        raise HTTPException(status_code=400, detail="Algorithm has no current version")
    if current.status != VERSION_STATUS_READY:
        raise HTTPException(status_code=400, detail="Algorithm current version is missing files")
    return record


def _save_upload_to_temp(upload: UploadFile, temp_dir: Path) -> Path:
    """把上传流保存到临时文件。

    Args:
        upload: 上传文件。
        temp_dir: 临时目录。

    Returns:
        临时 zip 文件路径。
    """
    zip_path = temp_dir / "upload.zip"
    with zip_path.open("wb") as target:
        shutil.copyfileobj(upload.file, target)
    return zip_path


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> dict[str, int]:
    """解压 zip 到 dest_dir（保留目录结构），返回 {相对路径: 字节大小}。

    Args:
        zip_path: zip 文件路径。
        dest_dir: 解压目标目录。

    Returns:
        文件清单（zip 内相对路径 → 字节大小）。

    Raises:
        HTTPException: 非法 zip、空包或包含路径穿越条目时 400。
    """
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid zip archive") from exc
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, int] = {}
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            if not parts or info.filename.startswith("/") or ".." in parts or ":" in parts[0]:
                raise HTTPException(status_code=400, detail=f"Zip entry has illegal path: {info.filename}")
            data = archive.read(info)
            target = dest_dir.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            manifest[PurePosixPath(*parts).as_posix()] = len(data)
    if not manifest:
        raise HTTPException(status_code=400, detail="Zip archive contains no files")
    return manifest


def _strip_single_wrapper_dir(extract_dir: Path) -> None:
    """剥离 zip 的单层包裹目录（用户直接把文件夹打成 zip 的常见情况）。

    当解压结果只有唯一一个顶层目录时，把其内容上移到根级，逐层重复。

    Args:
        extract_dir: 解压目录。
    """
    while True:
        entries = list(extract_dir.iterdir())
        if len(entries) != 1 or not entries[0].is_dir():
            return
        wrapper = entries[0]
        for child in list(wrapper.iterdir()):
            shutil.move(str(child), str(extract_dir / child.name))
        wrapper.rmdir()


def install_algorithm_zip(
    *,
    algorithm_id: UUID,
    code: str,
    engine_type: str,
    version: str,
    version_name: str | None,
    notes: str | None,
    upload: UploadFile,
) -> AlgorithmVersionResponse:
    """校验并安装一个算法版本 zip 到 storage/algorithms/<code>/<version>/。

    Args:
        algorithm_id: 所属算法 ID。
        code: 算法 code（目录名）。
        engine_type: 引擎类型（决定必需/可选文件校验）。
        version: 版本号（如 v1.0.0）。
        version_name: 版本名称，可空。
        notes: 备注，可空。
        upload: 上传的 zip 文件。

    Returns:
        新版本记录（status 按可选文件缺失情况为 READY/MISSING_FILES）。

    Raises:
        HTTPException: 引擎非法、zip 非法或缺必需文件时 400。
    """
    engine = ENGINE_TYPES.get(engine_type)
    if engine is None:
        raise HTTPException(status_code=400, detail=f"Unknown engineType: {engine_type}")
    install_dir = get_settings().storage_algorithm_dir / code / version
    with tempfile.TemporaryDirectory(prefix="videoai-algo-") as temp_root:
        temp_dir = Path(temp_root)
        zip_path = _save_upload_to_temp(upload, temp_dir)
        extract_dir = temp_dir / "extracted"
        manifest = _safe_extract_zip(zip_path, extract_dir)
        _strip_single_wrapper_dir(extract_dir)
        missing_required = [name for name in engine.requiredFiles if not (extract_dir / name).is_file()]
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required files at zip root: {', '.join(missing_required)}",
            )
        missing_optional = [name for name in engine.optionalFiles if not (extract_dir / name).is_file()]
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(extract_dir, install_dir)
    return AlgorithmVersionResponse(
        id=uuid4(),
        algorithmId=algorithm_id,
        version=version,
        versionName=version_name,
        notes=notes,
        status=VERSION_STATUS_MISSING_FILES if missing_optional else VERSION_STATUS_READY,
        missingFiles=missing_optional,
        fileManifest=manifest,
        active=False,
        createdAt=datetime.now(timezone.utc),
    )


def backup_current_version(record: AlgorithmRecord) -> Path | None:
    """把当前版本安装目录整体复制到 .backup/<旧version>-<UTC时间戳>/。

    Args:
        record: 算法内存记录。

    Returns:
        备份目录；无当前版本或目录不存在时返回 None。
    """
    if record.currentVersion is None:
        return None
    source = get_settings().storage_algorithm_dir / record.code / record.currentVersion
    if not source.is_dir():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = (
        get_settings().storage_algorithm_dir / record.code / ".backup" / f"{record.currentVersion}-{stamp}"
    )
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, backup_dir)
    return backup_dir


def create_algorithm(
    *,
    name: str,
    code: str,
    engine_type: str,
    version: str,
    scene: str | None,
    owner: str | None,
    description: str | None,
    version_name: str | None,
    notes: str | None,
    upload: UploadFile,
) -> AlgorithmRecord:
    """创建算法并安装首个版本，置 current_version。

    Args:
        name: 算法名称。
        code: 算法编码（唯一）。
        engine_type: 引擎类型。
        version: 首个版本号。
        scene: 场景，可空。
        owner: 负责人，可空。
        description: 描述，可空。
        version_name: 版本名称，可空。
        notes: 备注，可空。
        upload: 首个版本的 zip 包。

    Returns:
        新建算法内存记录。

    Raises:
        HTTPException: 引擎非法或 code 重复时 400；zip 校验失败时 400。
    """
    if engine_type not in ENGINE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown engineType: {engine_type}")
    if any(item.code == code for item in state.algorithms_store.values()):
        raise HTTPException(status_code=400, detail=f"Algorithm code already exists: {code}")
    now = datetime.now(timezone.utc)
    record = AlgorithmRecord(
        id=uuid4(),
        name=name,
        code=code,
        engineType=engine_type,
        scene=scene,
        owner=owner,
        description=description,
        createdAt=now,
        updatedAt=now,
    )
    version_response = install_algorithm_zip(
        algorithm_id=record.id,
        code=code,
        engine_type=engine_type,
        version=version,
        version_name=version_name,
        notes=notes,
        upload=upload,
    )
    record.versions[version_response.id] = version_response
    record.currentVersion = version
    state.algorithms_store[record.id] = record
    persist_algorithm(record)
    return record


def add_version(
    record: AlgorithmRecord,
    *,
    version: str,
    version_name: str | None,
    notes: str | None,
    upload: UploadFile,
) -> AlgorithmVersionResponse:
    """备份当前版本后安装新版本，并切换 current_version 指针。

    Args:
        record: 算法内存记录。
        version: 新版本号。
        version_name: 版本名称，可空。
        notes: 备注，可空。
        upload: 新版本 zip 包。

    Returns:
        新版本记录。

    Raises:
        HTTPException: 版本号重复或 zip 校验失败时 400。
    """
    if any(item.version == version for item in record.versions.values()):
        raise HTTPException(status_code=400, detail=f"Version already exists: {version}")
    backup_current_version(record)
    version_response = install_algorithm_zip(
        algorithm_id=record.id,
        code=record.code,
        engine_type=record.engineType,
        version=version,
        version_name=version_name,
        notes=notes,
        upload=upload,
    )
    record.versions[version_response.id] = version_response
    record.currentVersion = version
    record.updatedAt = datetime.now(timezone.utc)
    persist_algorithm(record)
    return version_response


def activate_version(record: AlgorithmRecord, version_id: UUID) -> AlgorithmVersionResponse:
    """备份当前版本后把 current_version 指针切换到指定版本。

    Args:
        record: 算法内存记录。
        version_id: 目标版本 ID。

    Returns:
        被激活的版本记录。

    Raises:
        HTTPException: 版本不存在时 404。
    """
    target = record.versions.get(version_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Algorithm version not found")
    if record.currentVersion != target.version:
        backup_current_version(record)
        record.currentVersion = target.version
        record.updatedAt = datetime.now(timezone.utc)
        persist_algorithm(record)
    return target


def update_algorithm(record: AlgorithmRecord, request: AlgorithmUpdateRequest) -> AlgorithmRecord:
    """部分更新算法字段（名称/场景/负责人/描述/状态）。

    Args:
        record: 算法内存记录。
        request: 更新请求；仅更新显式出现且非 None 的字段。

    Returns:
        更新后的内存记录。

    Raises:
        HTTPException: status 非法时 400。
    """
    if request.status is not None and request.status not in (ALGORITHM_STATUS_RUNNING, ALGORITHM_STATUS_DISABLED):
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    update_payload: dict[str, Any] = {"updatedAt": datetime.now(timezone.utc)}
    for field in ("name", "scene", "owner", "description", "status"):
        if field in request.model_fields_set:
            value = getattr(request, field)
            if value is not None:
                update_payload[field] = value
    updated = record.model_copy(update=update_payload)
    state.algorithms_store[record.id] = updated
    persist_algorithm(updated)
    return updated


def list_versions(record: AlgorithmRecord) -> list[AlgorithmVersionResponse]:
    """按创建时间倒序返回版本列表（active 按 current_version 计算）。

    Args:
        record: 算法内存记录。

    Returns:
        版本响应列表。
    """
    versions = sorted(record.versions.values(), key=lambda item: item.createdAt, reverse=True)
    return [item.model_copy(update={"active": item.version == record.currentVersion}) for item in versions]


def persist_algorithm(record: AlgorithmRecord) -> None:
    """把算法及其全部版本 upsert 到数据库；失败仅记录日志，不影响内存态。

    Args:
        record: 待持久化的算法内存记录。
    """
    try:
        with SessionLocal() as pgdb:
            row = pgdb.get(AlgorithmORM, record.id)
            if row is None:
                row = AlgorithmORM(id=record.id)
                pgdb.add(row)
            row.name = record.name
            row.code = record.code
            row.engine_type = record.engineType
            row.scene = record.scene
            row.status = record.status
            row.owner = record.owner
            row.description = record.description
            row.current_version = record.currentVersion
            row.created_at = record.createdAt
            row.updated_at = record.updatedAt
            for item in record.versions.values():
                version_row = pgdb.get(AlgorithmVersionORM, item.id)
                if version_row is None:
                    version_row = AlgorithmVersionORM(id=item.id)
                    pgdb.add(version_row)
                version_row.algorithm_id = record.id
                version_row.version = item.version
                version_row.version_name = item.versionName
                version_row.notes = item.notes
                version_row.status = item.status
                version_row.missing_files = list(item.missingFiles)
                version_row.file_manifest = dict(item.fileManifest)
                version_row.install_path = str(
                    get_settings().storage_algorithm_dir / record.code / item.version
                )
                version_row.created_at = item.createdAt
            pgdb.commit()
    except SQLAlchemyError as exc:
        logger.error("algorithm persist failed: %s", exc)


def load_algorithms_from_db() -> None:
    """启动时把数据库中的算法与版本载入内存存储；数据库不可达时以空集启动。"""
    try:
        with SessionLocal() as pgdb:
            rows = pgdb.query(AlgorithmORM).all()
            state.algorithms_store.clear()
            for row in rows:
                version_rows = (
                    pgdb.query(AlgorithmVersionORM)
                    .filter(AlgorithmVersionORM.algorithm_id == row.id)
                    .all()
                )
                versions = {
                    version_row.id: AlgorithmVersionResponse(
                        id=version_row.id,
                        algorithmId=version_row.algorithm_id,
                        version=version_row.version,
                        versionName=version_row.version_name,
                        notes=version_row.notes,
                        status=version_row.status,
                        missingFiles=list(version_row.missing_files or []),
                        fileManifest=dict(version_row.file_manifest or {}),
                        active=version_row.version == row.current_version,
                        createdAt=version_row.created_at,
                    )
                    for version_row in version_rows
                }
                state.algorithms_store[row.id] = AlgorithmRecord(
                    id=row.id,
                    name=row.name,
                    code=row.code,
                    engineType=row.engine_type,
                    scene=row.scene,
                    status=row.status,
                    owner=row.owner,
                    description=row.description,
                    currentVersion=row.current_version,
                    createdAt=row.created_at,
                    updatedAt=row.updated_at,
                    versions=versions,
                )
    except SQLAlchemyError as exc:  # 数据库不可达时以空算法集启动（与布控任务一致）
        logger.error("algorithm load failed: %s", exc)
