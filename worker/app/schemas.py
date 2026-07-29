from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import UUID


class EmbeddingResponse(BaseModel):
    embedding: List[float]


class FaceTarget(BaseModel):
    faceProfileId: UUID
    deploymentTaskId: Optional[UUID] = None
    recognitionPerMinute: int = Field(default=60, ge=1)


class StreamStartRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    streamUrl: str
    faceProfileId: Optional[UUID] = None
    deploymentTaskId: Optional[UUID] = None
    faceTargets: List[FaceTarget] = Field(default_factory=list)
    faceDetectionEnabled: bool = True
    objectDetectionEnabled: bool = False


class StreamStopRequest(BaseModel):
    cameraId: UUID


class StreamStatusResponse(BaseModel):
    streams: Dict[str, str]


class MatchRequest(BaseModel):
    embedding: List[float]
    threshold: Optional[float] = None
    faceProfileId: Optional[UUID] = None


class MatchResponse(BaseModel):
    matched: bool
    id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    photoPath: Optional[str] = None
    similarity: float = 0.0


class FaceEventIngestRequest(BaseModel):
    cameraId: UUID
    faceProfileId: UUID
    cameraName: str
    profileName: str
    profileDescription: Optional[str] = None
    facePhotoPath: str
    snapshotBase64: Optional[str] = None
    videoTime: datetime
    similarity: float
    deploymentTaskId: Optional[UUID] = None


class ObjectInfo(BaseModel):
    labelId: int
    labelName: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float


class ObjectEventIngestRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    objects: List[ObjectInfo]
    snapshotBase64: Optional[str] = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
