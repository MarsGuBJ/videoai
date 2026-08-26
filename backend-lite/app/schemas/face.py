"""人脸档案 / 人脸匹配 / 人脸扫描 DTO。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FaceProfileResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    photoUrl: str
    createdAt: datetime
    updatedAt: datetime


class FaceUploadRequest(BaseModel):
    imageBase64: str
    name: str | None = None
    cameraId: str
    modelName: str


class MatchRequest(BaseModel):
    embedding: list[float]
    threshold: float | None = None
    faceProfileId: UUID | None = None


class MatchResponse(BaseModel):
    matched: bool
    id: UUID | None = None
    name: str | None = None
    description: str | None = None
    photoPath: str | None = None
    similarity: float = 0.0


class FaceScanSummary(BaseModel):
    cameras: int
    faces: int
    framesCaptured: int
    faceDetections: int
    matches: int
    errors: list[str]
    scannedAt: datetime
