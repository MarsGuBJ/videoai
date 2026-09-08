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


class ObjectInfo(BaseModel):
    labelId: int
    labelName: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float


class DeploymentEventItem(BaseModel):
    """布控事件存储表（deployment_events）的对外条目。"""

    id: UUID
    deploymentTaskId: UUID | None = None
    eventType: str
    algorithmCode: str | None = None
    reviewStatus: str | None = None
    faceProfileId: UUID | None = None
    faceProfileName: str | None = None
    faceProfilePhotoUrl: str | None = None
    objects: list[ObjectInfo] | None = None
    frameWidth: int = 0
    frameHeight: int = 0
    snapshotUrl: str | None = None
    cameraId: UUID | None = None
    cameraName: str | None = None
    cameraArea: str | None = None
    similarity: float | None = None
    occurredAt: datetime
    createdAt: datetime


class DeploymentEventPage(BaseModel):
    """布控事件分页响应。"""

    items: list[DeploymentEventItem]
    total: int
    page: int
    size: int


class DeploymentEventSummary(BaseModel):
    """布控事件统计卡数据。"""

    total: int
    today: int
    faceMatch: int
    objectDetection: int


class DeploymentEventTrendItem(BaseModel):
    """事件趋势单日计数。"""

    date: str
    count: int


class DeploymentEventAreaItem(BaseModel):
    """区域事件排行条目。"""

    area: str
    count: int


class DeploymentEventReviewItem(BaseModel):
    """按事件大类统计的复核情况。"""

    eventType: str
    valid: int
    invalid: int
    unreviewed: int


class DeploymentEventStats(BaseModel):
    """事件统计页聚合数据。"""

    total: int
    today: int
    week: int
    unreviewed: int
    reviewRate: float
    faceMatch: int
    objectDetection: int
    areas: list[str]
    trend: list[DeploymentEventTrendItem]
    byArea: list[DeploymentEventAreaItem]
    reviewByType: list[DeploymentEventReviewItem]


class ObjectEventResponse(BaseModel):
    id: UUID
    cameraId: UUID
    cameraName: str
    objects: list[ObjectInfo]
    snapshotUrl: str | None = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0
    eventType: str | None = None
    deploymentTaskId: UUID | None = None
    createdAt: datetime


class ObjectEventIngestRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    objects: list[ObjectInfo]
    snapshotBase64: str | None = None
    videoTime: datetime
    frameWidth: int = 0
    frameHeight: int = 0
    eventType: str | None = None
    deploymentTaskId: UUID | None = None
