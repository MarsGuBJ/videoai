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
    # 快照相似度百分比（0-100，如 96 表示两张截图相似度 96%），与布控任务的人物/车辆相似度无关
    similarity: float | None = Field(default=None, ge=0, le=100)
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
    # 快照相似度百分比（0-100，如 96 表示两张截图相似度 96%），与布控任务的人物/车辆相似度无关
    similarity: float | None = Field(default=None, ge=0, le=100)
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
