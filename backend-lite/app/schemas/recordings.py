"""NVR 录像检索 / 回放 / 下载代理 DTO。"""

from typing import Any

from pydantic import BaseModel


class RecordingSearchRequest(BaseModel):
    cameraId: str
    startTime: str
    endTime: str
    # 回放倍速，仅 /api/recordings/stream 使用；现场海康 NVR 实测支持 0.25~32 倍
    speed: float | None = None


class RecordingSegment(BaseModel):
    """MCP search_recordings 返回的单段录像。"""

    recordingId: str
    cameraId: str
    cameraName: str | None = None
    trackId: str | None = None
    startTime: str
    endTime: str
    source: str | None = None
    url: str | None = None
    format: str | None = None
    metadata: dict[str, Any] = {}


class RecordingSearchResponse(BaseModel):
    data: list[RecordingSegment]


class RecordingStreamResponse(BaseModel):
    url: str
    format: str
    expiresAt: str | None = None


class RecordingDownloadResponse(BaseModel):
    url: str
    format: str
