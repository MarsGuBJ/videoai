from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class EmbeddingResponse(BaseModel):
    embedding: list[float]


class FaceTarget(BaseModel):
    faceProfileId: UUID
    deploymentTaskId: UUID | None = None
    # 字段名为历史遗留：语义为每次采样的间隔秒数（设置 x 则每 x 秒采样一次）
    recognitionPerMinute: int = Field(default=60, ge=1)


class AlgorithmSpec(BaseModel):
    """算法引擎描述：backend-lite 安装到共享算法目录后下发给 worker。"""

    algorithmId: UUID
    engineType: str
    version: str
    installPath: str
    # 字段名为历史遗留：语义为每次采样的间隔秒数
    recognitionPerMinute: int = Field(default=60, ge=1)
    # 算法事件归属的布控任务；缺省时回退到 StreamStartRequest.deploymentTaskId
    deploymentTaskId: UUID | None = None


class StreamStartRequest(BaseModel):
    cameraId: UUID
    cameraName: str
    streamUrl: str
    faceProfileId: UUID | None = None
    deploymentTaskId: UUID | None = None
    faceTargets: list[FaceTarget] = Field(default_factory=list)
    faceDetectionEnabled: bool = True
    objectDetectionEnabled: bool = False
    # 旧字段：单一算法。同一摄像头绑定多个算法任务时由 backend-lite 下发 algorithms
    algorithm: AlgorithmSpec | None = None
    algorithms: list[AlgorithmSpec] = Field(default_factory=list)

    @property
    def algorithm_specs(self) -> list[AlgorithmSpec]:
        """合并 algorithms 与旧字段 algorithm，按 algorithmId 去重并保持顺序。"""
        specs: list[AlgorithmSpec] = []
        seen: set[UUID] = set()
        for spec in [*self.algorithms, *(spec for spec in [self.algorithm] if spec is not None)]:
            if spec.algorithmId in seen:
                continue
            seen.add(spec.algorithmId)
            specs.append(spec)
        return specs


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
    eventType: str | None = None
    deploymentTaskId: UUID | None = None


def utc_now() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
