"""算法管理 DTO（对外字段一律 camelCase，与 deployment_task 一致）。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EngineTypeInfo(BaseModel):
    engineType: str
    label: str
    requiredFiles: list[str]
    optionalFiles: list[str] = []
    description: str = ""


class AlgorithmVersionResponse(BaseModel):
    id: UUID
    algorithmId: UUID
    version: str
    versionName: str | None = None
    notes: str | None = None
    status: str
    missingFiles: list[str] = []
    fileManifest: dict[str, int] = {}
    active: bool = False
    createdAt: datetime


class AlgorithmResponse(BaseModel):
    id: UUID
    name: str
    code: str
    engineType: str
    engineLabel: str
    scene: str | None = None
    status: str
    owner: str | None = None
    description: str | None = None
    currentVersion: str | None = None
    versionCount: int = 0
    currentVersionStatus: str | None = None
    missingFiles: list[str] = []
    createdAt: datetime
    updatedAt: datetime


class AlgorithmUpdateRequest(BaseModel):
    name: str | None = None
    scene: str | None = None
    owner: str | None = None
    description: str | None = None
    status: str | None = None


class AlgorithmRecord(BaseModel):
    """内存态算法记录：算法字段 + 版本表（持久化到 algorithms/algorithm_versions）。"""

    id: UUID
    name: str
    code: str
    engineType: str
    scene: str | None = None
    status: str = "RUNNING"
    owner: str | None = None
    description: str | None = None
    currentVersion: str | None = None
    createdAt: datetime
    updatedAt: datetime
    versions: dict[UUID, AlgorithmVersionResponse] = {}
