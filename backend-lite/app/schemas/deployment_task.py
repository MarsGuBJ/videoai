"""布控任务 DTO。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

DEFAULT_RECOGNITION_PER_MINUTE = 60


class DeploymentTaskResponse(BaseModel):
    id: UUID
    name: str
    pipeline: str
    area: str
    areaCount: int
    enabled: bool
    taskStatus: str
    desc: str
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = None
    cameraIds: list[str]
    recognitionPerMinute: int = Field(default=DEFAULT_RECOGNITION_PER_MINUTE, ge=1)
    algorithmId: UUID | None = None
    algorithmName: str | None = None
    engineType: str | None = None
    algorithmCode: str | None = None
    createdAt: datetime
    updatedAt: datetime


class DeploymentTaskCreateRequest(BaseModel):
    name: str
    pipeline: str = "人脸识别流程"
    area: str | None = None
    areaCount: int = 0
    enabled: bool = True
    desc: str = ""
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = None
    cameraIds: list[str] = []
    recognitionPerMinute: int = Field(default=DEFAULT_RECOGNITION_PER_MINUTE, ge=1)
    algorithmId: UUID | None = None
    algorithmCode: str | None = None


class DeploymentTaskUpdateRequest(BaseModel):
    name: str | None = None
    pipeline: str | None = None
    area: str | None = None
    areaCount: int | None = None
    enabled: bool | None = None
    taskStatus: str | None = None
    desc: str | None = None
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = None
    cameraIds: list[str] | None = None
    recognitionPerMinute: int | None = Field(default=None, ge=1)
    algorithmId: UUID | None = None
    algorithmCode: str | None = None
