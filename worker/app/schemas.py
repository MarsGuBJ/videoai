from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class EmbeddingResponse(BaseModel):
    embedding: list[float]


class FaceTarget(BaseModel):
    faceProfileId: UUID
    deploymentTaskId: UUID | None = None
    recognitionPerMinute: int = Field(default=60, ge=1)


class StreamStartRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    streamUrl: str
    faceProfileId: UUID | None = None
    deploymentTaskId: UUID | None = None
    faceTargets: list[FaceTarget] = Field(default_factory=list)
    faceDetectionEnabled: bool = True
    objectDetectionEnabled: bool = False


class StreamStopRequest(BaseModel):
    cameraId: UUID


class StreamStatusResponse(BaseModel):
    streams: dict[str, str]


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
    objects: list[ObjectInfo]
    snapshotBase64: str | None = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0


def utc_now() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
