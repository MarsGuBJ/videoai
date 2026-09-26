"""布控任务 DTO。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

DEFAULT_RECOGNITION_PER_MINUTE = 60
DEFAULT_SIMILARITY = 50


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
    similarity: int = Field(default=DEFAULT_SIMILARITY, ge=0, le=100)
    effectiveStart: str | None = None
    effectiveEnd: str | None = None
    cycleStart: str | None = None
    cycleEnd: str | None = None
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
    similarity: int = Field(default=DEFAULT_SIMILARITY, ge=0, le=100)
    effectiveStart: str | None = None
    effectiveEnd: str | None = None
    cycleStart: str | None = None
    cycleEnd: str | None = None
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
    similarity: int | None = Field(default=None, ge=0, le=100)
    effectiveStart: str | None = None
    effectiveEnd: str | None = None
    cycleStart: str | None = None
    cycleEnd: str | None = None
    algorithmId: UUID | None = None
    algorithmCode: str | None = None
