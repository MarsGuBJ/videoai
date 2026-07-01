from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Camera(BaseModel):
    id: str
    name: str
    sourceUrl: str
    streamApp: str
    streamName: str
    ffmpegKey: str | None = None
    description: str | None = None
    status: str
    playbackUrl: str
    createdAt: datetime
    updatedAt: datetime
    nvrId: str | None = None
    nvrChannel: str | None = None
    nvrTrackId: str | None = None
    nvrStreamType: str | None = None

    @property
    def nvr_bound(self) -> bool:
        return bool(self.nvrTrackId or self.nvrChannel)

    @property
    def track_id(self) -> str | None:
        return self.nvrTrackId or self.nvrChannel


class RecordingSegment(BaseModel):
    recordingId: str
    cameraId: str
    cameraName: str
    trackId: str
    startTime: datetime
    endTime: datetime
    playbackUri: str = Field(exclude=True)
    source: str = "hikvision_nvr_recording"
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamResponse(BaseModel):
    url: str
    format: str
    expiresAt: datetime | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
