"""事件（人脸事件 / 目标事件 / 匹配事件）DTO。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FaceEventResponse(BaseModel):
    id: UUID
    cameraId: UUID
    faceProfileId: UUID
    cameraName: str
    profileName: str
    profileDescription: str | None = None
    facePhotoUrl: str
    snapshotUrl: str | None = None
    videoTime: datetime
    similarity: float
    createdAt: datetime


class FaceEventIngestRequest(BaseModel):
    cameraId: UUID
    faceProfileId: UUID
    cameraName: str
    profileName: str
    profileDescription: str | None = None
    facePhotoPath: str
    snapshotBase64: str | None = None
    videoTime: datetime
    similarity: float
    deploymentTaskId: UUID | None = None


class FaceMatchEventResponse(BaseModel):
    id: UUID
    deploymentTaskId: UUID | None = None
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = None
    snapshotUrl: str | None = None
    cameraId: UUID | None = None
    cameraName: str | None = None
    cameraArea: str | None = None
    similarity: float
    matchedAt: datetime
    createdAt: datetime


class ObjectInfo(BaseModel):
    labelId: int
    labelName: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float


class ObjectEventResponse(BaseModel):
    id: UUID
    cameraId: UUID
    cameraName: str
    objects: list[ObjectInfo]
    snapshotUrl: str | None = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0
    createdAt: datetime


class ObjectEventIngestRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    objects: list[ObjectInfo]
    snapshotBase64: str | None = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0
