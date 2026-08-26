"""摄像头 DTO。

CameraResponse 独立于此模块（而非依赖服务层），是根治
camera_cache <-> main 循环依赖的关键：camera_cache 只需依赖本 schema。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CameraResponse(BaseModel):
    """Java media backend 返回的摄像头结构（字段名为对外 camelCase 契约）。"""

    id: UUID
    name: str
    sourceUrl: str
    streamApp: str
    streamName: str
    ffmpegKey: str | None = None
    description: str | None = None
    area: str | None = None
    status: str
    playbackUrl: str
    createdAt: datetime
    updatedAt: datetime
    nvrId: str | None = None
    nvrChannel: str | None = None
    nvrTrackId: str | None = None
    nvrStreamType: str | None = None
    protocol: str | None = None
    vendor: str | None = None
    ip: str | None = None
    port: str | None = None
    username: str | None = None
    password: str | None = None
    deviceCode: str | None = None
    serialNumber: str | None = None
    objectDetectionEnabled: bool = False
