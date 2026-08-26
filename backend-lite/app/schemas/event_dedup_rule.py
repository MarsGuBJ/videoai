"""事件去重规则 DTO（对外契约 camelCase）。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DedupStrategy = Literal["时间维度去重", "区间重叠图像去重", "实时重叠图像去重"]


class DedupRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    algorithm: str = ""
    strategy: DedupStrategy = "时间维度去重"
    durationMinutes: int | None = None
    similarity: float | None = None
    allCameras: bool = True
    cameras: list[str] = Field(default_factory=list)
    remark: str = ""
    enabled: bool = True


class DedupRuleUpdate(BaseModel):
    """全字段可选；缺省表示保留原值。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    algorithm: str | None = None
    strategy: DedupStrategy | None = None
    durationMinutes: int | None = None
    similarity: float | None = None
    allCameras: bool | None = None
    cameras: list[str] | None = None
    remark: str | None = None
    enabled: bool | None = None


class DedupRuleOut(BaseModel):
    id: str
    name: str
    algorithm: str
    strategy: DedupStrategy
    durationMinutes: int | None
    similarity: float | None
    allCameras: bool
    cameras: list[str]
    remark: str
    enabled: bool
    createdAt: datetime
    updatedAt: datetime
