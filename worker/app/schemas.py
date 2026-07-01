from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import UUID


class EmbeddingResponse(BaseModel):
    embedding: List[float]


class StreamStartRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    streamUrl: str


class StreamStopRequest(BaseModel):
    cameraId: UUID


class StreamStatusResponse(BaseModel):
    streams: Dict[str, str]


class MatchRequest(BaseModel):
    embedding: List[float]
    threshold: Optional[float] = None


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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

